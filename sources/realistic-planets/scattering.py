"""Single scattering of sunlight in a body's haze, as the mod's `haze.glsl` works it out for each
pixel, for the bodies' fits (`titan/haze.py`, `neptune/haze.py`).

- A sky point's I/F is the sunlight that the haze along its line of sight scatters toward the camera
  once: omega P(theta) / 4 times the integral of the extinction along the line, each point weighted
  by the share of the sunlight that reaches it, exp(-tau_sun), and the share of the light it
  scatters that reaches the camera, exp(-tau_view). Light scattered more than once is left out.
- The main haze's extinction falls exponentially with height. tau_sun is its optical depth toward
  the sun, Chapman's grazing-incidence integral (S. Chapman, Proc. Phys. Soc. 43, 1931): at radius
  r, with x = r / H, the extinction there times H sqrt(pi x / 2) exp(y^2) erfc(y),
  y = sqrt(x / 2) cos chi, for a sun cos chi above the horizon; below it, twice the integral from
  the line's lowest point, less that back from r.
- The phase function is made of Henyey-Greenstein lobes (L. G. Henyey and J. L. Greenstein, ApJ 93,
  1941) and Rayleigh's, (3/4) (1 + cos^2 theta), for the gas.
"""
import numpy as np
from scipy.special import erfcx


def lobe(g, cos_theta):
    """Henyey and Greenstein's phase function of asymmetry `g`, at the scattering angle's cosine."""
    return (1 - g * g) / (1 + g * g - 2 * g * cos_theta) ** 1.5


def rayleigh(cos_theta):
    """Rayleigh's phase function, at the scattering angle's cosine."""
    return 0.75 * (1 + cos_theta * cos_theta)


def phase_function(cos_theta, first_lobe, second_lobe, first_share, second_share):
    """The haze's phase function at the scattering angle's cosine, as `haze.glsl` has it: two
    Henyey-Greenstein lobes, with their asymmetries and their shares of the light, and Rayleigh's
    with the rest."""
    rest = 1 - first_share - second_share
    return first_share * lobe(first_lobe, cos_theta) + second_share * lobe(second_lobe, cos_theta) + rest * rayleigh(cos_theta)


def main_haze(r, reference, log_extinction, scale):
    """The main haze's extinction at radius r, km: exp(`log_extinction`) per km at the radius
    `reference`, falling by e every `scale` km above it."""
    return np.exp(np.minimum(log_extinction - (r - reference) / scale, 600.0))


def toward_sun(r, cos_chi, reference, log_extinction, scale):
    """The main haze's optical depth from radius r toward the sun, cos_chi from the vertical."""
    x = r / scale
    here = main_haze(r, reference, log_extinction, scale) * scale * np.sqrt(np.pi * x / 2) * erfcx(np.sqrt(x / 2) * np.abs(cos_chi))
    lowest = r * np.sqrt(np.clip(1 - cos_chi ** 2, 0, 1))
    through = 2 * main_haze(lowest, reference, log_extinction, scale) * scale * np.sqrt(np.pi * (lowest / scale) / 2)
    return np.where(cos_chi >= 0, here, through - here)


def sky_light(x, y, phase, extinction, sun_depth, top, steps, spread):
    """The integral along the lines of sight through sky points (x, y), km from the body's centre,
    the sun's direction along x, seen from afar at `phase` degrees, of `extinction(r)` times the
    sunlight reaching each point, exp(-`sun_depth(r, cos_chi)`), and the share of its light that
    gets out toward the camera. The lines are followed up to the radius `top`, in `steps` steps,
    closest where they pass nearest the body, as `spread` says. omega P(theta) / 4 times it is the
    I/F."""
    a = np.radians(phase)
    sun = np.array([np.sin(a), 0.0, np.cos(a)])
    through = np.hypot(x, y)
    chord = np.sqrt(np.clip(top ** 2 - through ** 2, 0, None))
    u = np.linspace(-1, 1, steps)
    along = chord[..., None] * np.sinh(spread * u) / np.sinh(spread)
    step = chord[..., None] * spread * np.cosh(spread * u) / np.sinh(spread) * (u[1] - u[0])
    r = np.sqrt(through[..., None] ** 2 + along ** 2)
    cos_chi = (x[..., None] * sun[0] + y[..., None] * sun[1] + along * sun[2]) / r
    piece = extinction(r) * step
    # The depth from each step to the camera, at +along: the steps beyond it.
    depth = np.cumsum(piece[..., ::-1], axis=-1)[..., ::-1] - 0.5 * piece
    return np.sum(piece * np.exp(-sun_depth(r, cos_chi) - depth), axis=-1)


def iof(x, y, phase, reference, log_extinction, scale, albedo, lobes, top, steps, spread, layer=None):
    """The haze's I/F at sky points (x, y), km from the body's centre, the sun's direction along x,
    seen from afar at `phase` degrees, as `haze.glsl` works it out: the main haze's extinction
    (`main_haze`), with a detached layer's, `layer(r)`, where there is one, which is optically thin
    and left out of the sunlight's depth; the single-scattering albedo; and the phase function's
    lobes and shares (`phase_function`). The lines of sight are followed as `sky_light` follows
    them."""
    def extinction(r):
        main = main_haze(r, reference, log_extinction, scale)
        return main if layer is None else main + layer(r)

    def sun_depth(r, cos_chi):
        return toward_sun(r, cos_chi, reference, log_extinction, scale)

    light = sky_light(x, y, phase, extinction, sun_depth, top, steps, spread)
    return albedo * phase_function(-np.cos(np.radians(phase)), *lobes) * light / 4


def vec3(values, digits):
    """A GLSL vec3 of `values`, to `digits` significant digits."""
    return 'vec3(' + ', '.join(f'{v:.{digits}g}' for v in values) + ')'


def constructor(name, unit, reference, top, extinction, scale, layer, layer_radius, layer_width, texture_cosine,
                albedo, first_lobe, second_lobe, first_share, second_share, colour, bloom):
    """The `RealisticPlanetsHaze` that `haze.glsl` takes, called `name`, as GLSL: its fields in their
    order, each filter's numbers as a vec3, and `colour` the matrix's columns, one for each
    filter."""
    fields = [f'{unit:.1f}', f'{reference:.1f}', f'{top:.1f}', vec3(extinction, 4), vec3(scale, 4), vec3(layer, 4),
              vec3(layer_radius, 5), vec3(layer_width, 3), f'{texture_cosine:.3f}', vec3(albedo, 3), vec3(first_lobe, 3),
              vec3(second_lobe, 3), vec3(first_share, 3), vec3(second_share, 3),
              'mat3(' + ', '.join(f'{v:.5f}' for column in colour for v in column) + ')', f'{bloom:g}']
    return f'const RealisticPlanetsHaze {name} = RealisticPlanetsHaze(\n    ' + ',\n    '.join(fields) + ');'
