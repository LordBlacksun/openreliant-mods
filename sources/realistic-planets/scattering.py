"""Sunlight scattered by a body's haze, as the mod's `haze.glsl` works it out for each pixel, for the
bodies' fits (`titan/haze.py`, `neptune/haze.py`).

- A sky point's I/F is first the sunlight that the haze along its line of sight scatters toward the
  camera once: omega P(theta) / 4 times the integral of the extinction along the line, each point
  weighted by the share of the sunlight that reaches it, exp(-tau_sun), and the share of the light
  it scatters that reaches the camera, exp(-tau_view).
- The light scattered more than once is an estimate (`multiple_light`), whose numbers are fitted to
  a Monte Carlo of all orders of scattering in the same haze (`multiple.py`).
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


# The most optical depth along the light's path the estimate of the light scattered more than once
# takes, as the shader does, past which e^-t is below 1e-34.
MOST_DEPTH = 80.0
# The wavelengths a haze built from measurements of its particles is worked out at, nm, in blue, green
# and red (`mie.py`).
WAVELENGTHS = {'blue': 450.0, 'green': 550.0, 'red': 650.0}


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


class Haze:
    """One filter's haze, as the model has it: the main haze's extinction exp(`log_extinction`) per km
    at the radius `reference`, falling by e every `scale` km (`main_haze`), with a detached layer's,
    `layer(r)`, where there is one, which is optically thin and left out of the sunlight's depth; the
    single-scattering albedo; the phase function's lobes and shares (`phase_function`); the radius
    the haze is cut off at; and the radius below which the Monte Carlo's paths end (`multiple.py`),
    at the body's solid surface or deeper."""

    def __init__(self, reference, log_extinction, scale, albedo, lobes, top, floor, layer=None):
        self.reference, self.log_extinction, self.scale = reference, log_extinction, scale
        self.albedo, self.lobes, self.top, self.floor, self.layer = albedo, lobes, top, floor, layer

    def extinction(self, r):
        """The extinction at radius r, km, per km."""
        main = main_haze(r, self.reference, self.log_extinction, self.scale)
        return main if self.layer is None else main + self.layer(r)

    def sun_depth(self, r, cos_chi):
        """The optical depth toward the sun from radius r, the sun cos_chi from the vertical
        (`toward_sun`)."""
        return toward_sun(r, cos_chi, self.reference, self.log_extinction, self.scale)


def sky_lines(x, y, phase, haze, steps, spread):
    """The steps along the lines of sight through sky points (x, y), km from the body's centre, the
    sun's direction along x, seen from afar at `phase` degrees: each step's extinction times its
    length; the optical depths toward the sun and toward the camera; the step's radius; and the sun's
    cosine there. The lines are followed up to the haze's top, in `steps` steps, closest where they
    pass nearest the body, as `spread` says."""
    a = np.radians(phase)
    sun = np.array([np.sin(a), 0.0, np.cos(a)])
    through = np.hypot(x, y)
    chord = np.sqrt(np.clip(haze.top ** 2 - through ** 2, 0, None))
    u = np.linspace(-1, 1, steps)
    along = chord[..., None] * np.sinh(spread * u) / np.sinh(spread)
    step = chord[..., None] * spread * np.cosh(spread * u) / np.sinh(spread) * (u[1] - u[0])
    r = np.sqrt(through[..., None] ** 2 + along ** 2)
    cos_chi = (x[..., None] * sun[0] + y[..., None] * sun[1] + along * sun[2]) / r
    piece = haze.extinction(r) * step
    # The depth from each step to the camera, at +along: the steps beyond it.
    depth = np.cumsum(piece[..., ::-1], axis=-1)[..., ::-1] - 0.5 * piece
    return piece, haze.sun_depth(r, cos_chi), depth, r, cos_chi


def multiple_light(lines, haze, cos_theta, numbers):
    """The light the haze scatters more than once along the lines (`sky_lines`), seen at the
    scattering angle's cosine `cos_theta`, as `haze.glsl` estimates it, in I/F, with `numbers` (beam,
    glow, fall, middle, width) fitted to a Monte Carlo (`multiple.py`):

    - A beam: sunlight scattered forward again on its way to the camera. With n scatterings in all,
      n = 2 and 3, its chance at a step is e^-t (beam t)^(n-1) / (n-1)!, for t the optical depth
      toward the sun and toward the camera; each scattering takes the albedo, and the phase
      function is the lobes convolved n times, each lobe's asymmetry to the n-th power.
    - A glow: light scattered many times, the same in every direction, `glow` times the sunlight at
      the haze's reference radius, falling by e every `fall` km up, and fading through the
      terminator, half where the sun's cosine is `middle`, over a few `width`s of it."""
    piece, to_sun, depth, r, cos_chi = lines
    beam, glow, fall, middle, width = numbers
    first, second, first_share, second_share = haze.lobes
    # Past `MOST_DEPTH` optical depths no light gets through, and t^2 would overflow.
    t = np.minimum(to_sun + depth, MOST_DEPTH)
    light = 0.0
    for n, chance in ((2, beam), (3, beam * beam / 2)):
        orders = phase_function(cos_theta, first ** n, second ** n, first_share, second_share)
        light = light + haze.albedo ** n * orders / 4 * chance * np.sum(piece * np.exp(-t) * t ** (n - 1), axis=-1)
    source = glow * np.exp(-(r - haze.reference) / fall) / (1 + np.exp(-(cos_chi - middle) / width))
    return light + haze.albedo / 4 * np.sum(piece * np.exp(-depth) * source, axis=-1)


def iof(x, y, phase, haze, steps, spread, multiple=None):
    """The haze's I/F at sky points (x, y), km from the body's centre, the sun's direction along x,
    seen from afar at `phase` degrees, as `haze.glsl` works it out: the light it scatters once, and
    with `multiple`, the estimate's numbers, the light it scatters more than once (`multiple_light`).
    The lines of sight are followed as `sky_lines` follows them."""
    lines = sky_lines(x, y, phase, haze, steps, spread)
    piece, to_sun, depth, r, cos_chi = lines
    cos_theta = -np.cos(np.radians(phase))
    light = haze.albedo * phase_function(cos_theta, *haze.lobes) / 4 * np.sum(piece * np.exp(-to_sun - depth), axis=-1)
    if multiple is not None:
        light = light + multiple_light(lines, haze, cos_theta, multiple)
    return light


def vec3(values, digits):
    """A GLSL vec3 of `values`, to `digits` significant digits."""
    return 'vec3(' + ', '.join(f'{v:.{digits}g}' for v in values) + ')'


def constructor(name, unit, reference, top, extinction, scale, layer, layer_radius, layer_width, texture_cosine,
                albedo, first_lobe, second_lobe, first_share, second_share, multiple, colour, bloom, polar=1.0, ring_unit=None):
    """The `RealisticPlanetsHaze` that `haze.glsl` takes, called `name`, as GLSL: its fields in their
    order, each filter's numbers as a vec3, `multiple` each filter's (beam, glow, fall, middle,
    width), or none for no light scattered more than once, and `colour` the matrix's columns, one
    for each filter. `polar` is a flattened body's polar radius as a share of `unit`, and
    `ring_unit` the unit of the ring the haze beyond the disk is drawn on, km, `unit` by default."""
    if multiple is None:
        # No beam and no glow; the glow's fall and width only need to be other than 0.
        multiple = [(0.0, 0.0, 1.0, 0.0, 1.0)] * 3
    beam, glow, fall, middle, width = np.array(multiple).T
    fields = [f'{unit:.1f}', f'{polar:.4f}', f'{unit if ring_unit is None else ring_unit:.1f}', f'{reference:.1f}', f'{top:.1f}',
              vec3(extinction, 4), vec3(scale, 4), vec3(layer, 4),
              vec3(layer_radius, 5), vec3(layer_width, 3), f'{texture_cosine:.3f}', vec3(albedo, 3), vec3(first_lobe, 3),
              vec3(second_lobe, 3), vec3(first_share, 3), vec3(second_share, 3), vec3(beam, 3), vec3(glow, 3), vec3(fall, 4),
              vec3(middle, 3), vec3(width, 3), 'mat3(' + ', '.join(f'{v:.5f}' for column in colour for v in column) + ')', f'{bloom:g}']
    return f'const RealisticPlanetsHaze {name} = RealisticPlanetsHaze(\n    ' + ',\n    '.join(fields) + ');'
