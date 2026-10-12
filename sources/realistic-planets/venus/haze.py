"""Works out Venus's upper haze for the mod's `venus.glsl` from what Venus Express measured of it, and
prints the shader's numbers. Run `compose.py` first: it writes `data/colour.json`, which turns the
haze's I/F into the texture's colours.

    python3 haze.py data

The open archives hold no frames of Venus's limb sharp enough to fit the haze to, as Titan's,
Neptune's and Saturn's are: Venus Express's camera saw the limb from its apocentre at about 40 km a
pixel, and the haze's scale height is a few km. So the haze is built from what SPICAV IR measured
of it in 222 solar occultations from 2006 to 2014 (Luginin and others, 2016):

- Its droplets come in two sizes, with effective radii of 0.12 and 0.84 micrometres, about 500 and 1
  a cubic centimetre at 75 km (`MODES`). Each spreads as a log-normal of effective variance
  `VARIANCE`, as the polarisation of Venus's clouds shows their droplets do (Hansen and Hovenier,
  1974).
- They're droplets of sulphuric acid, whose refractive index in visible light the same polarisation
  gives, about 1.44, a little more in blue and less in red (`INDEX`). They absorb next to none of it.
- Mie theory (`miepython`) gives each size's cross-section and phase function at each of the haze's
  wavelengths (`photometry.HAZE`). The haze's extinction at 75 km is the droplets' number times
  their cross-section, and its single-scattering albedo the droplets'.
- The extinction falls exponentially above, with the aerosol scale height SPICAV IR measured, 3.3
  km (`SCALE`).
- The model's phase function, two Henyey-Greenstein lobes and Rayleigh's for the rest of the light
  (`scattering.phase_function`), is fitted to the droplets' by least squares on its logarithm, at
  every degree of the scattering angle. The angles within `FORWARD` degrees of the forward direction,
  where a backlit haze's light comes from, count `FORWARD_WEIGHT` times as much. The fit follows the
  forward peak within about 10%, and the rest within about 20 to 30%, short of the droplets' glory
  near the backward direction.

The game's sphere is Venus's cloud tops, about 70 km up, which Akatsuki's maps in the texture show
(`UNIT`). The light the haze scatters more than once isn't estimated, as for Saturn's.
"""
import json
import os
import sys

import miepython
import numpy as np
from scipy import optimize

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import photometry  # noqa: E402
import scattering  # noqa: E402

# Venus's radius at its cloud tops, km: its solid radius, 6,051.8 km (IAU), and 70 km.
UNIT = 6121.8
# The height the extinction is given at, km above `UNIT`, 75 km up, where the droplets' numbers are
# measured; and the height the haze is cut off at, where its extinction is a hundred-millionth of the
# edge's or less.
REFERENCE = 5.0
TOP = 60.0
# The droplets' two sizes: each one's effective radius, micrometres, and its number a cubic
# centimetre at 75 km; and their effective variance.
MODES = [(0.12, 500.0), (0.84, 1.0)]
VARIANCE = 0.07
# Their refractive index at each of the haze's wavelengths, nm.
INDEX = {450.0: 1.45, 550.0: 1.44, 650.0: 1.43}
# The aerosol scale height, km.
SCALE = 3.3
# The radii each size is summed over: `RADII` of them, spread over `REACH` of its log-normal's widths
# either side of its middle.
RADII = 200
REACH = 4.0
# The phase function's fit: the angles from the forward direction that count `FORWARD_WEIGHT` times
# as much, degrees, and the first guesses it starts from, the best of which it keeps: the lobes'
# asymmetries, the first's share, and the second's share of what's left.
FORWARD = 30.0
FORWARD_WEIGHT = 3.0
FIRST_GUESSES = [(0.9, 0.5, 0.2, 0.9), (0.95, 0.6, 0.1, 0.8), (0.8, 0.0, 0.5, 0.5), (0.7, -0.3, 0.8, 0.5)]
LOWEST = (0.0, -0.95, 0.0, 0.0)
HIGHEST = (0.995, 0.95, 1.0, 1.0)
# How much of the haze's light blooms, which the mod chooses rather than the fit: a quarter, as for
# the other bodies.
BLOOM = 0.25


def droplets(radius, variance, wavelength):
    """Droplets of effective radius `radius` and effective variance `variance`, micrometres, in a
    log-normal, at `wavelength` nm: each one's mean extinction and scattering cross-section, square
    micrometres, and their phase function at every degree from 0 to 180 (`scattering.phase_function`'s
    normalisation)."""
    width = np.sqrt(np.log(1 + variance))
    middle = radius / (1 + variance) ** 2.5
    logs = np.linspace(np.log(middle) - REACH * width, np.log(middle) + REACH * width, RADII)
    weights = np.exp(-0.5 * ((logs - np.log(middle)) / width) ** 2)
    weights /= weights.sum()
    m = complex(INDEX[wavelength], 0.0)
    mu = np.cos(np.radians(np.arange(181.0)))
    extinction = scattered = 0.0
    phase = np.zeros(181)
    for r, weight in zip(np.exp(logs), weights):
        q_ext, q_sca, _, _ = miepython.efficiencies(m, 2 * r, wavelength / 1000)
        area = np.pi * r * r
        extinction += weight * area * q_ext
        scattered += weight * area * q_sca
        phase += weight * area * q_sca * miepython.i_unpolarized(m, 2 * np.pi * r * 1000 / wavelength, mu, norm='4pi')
    return extinction, scattered, phase / scattered


def lobes(phase):
    """The phase function that best follows `phase`, at every degree from 0 to 180, on its logarithm:
    two Henyey-Greenstein lobes' asymmetries and their shares of the light, Rayleigh's taking the
    rest."""
    angles = np.arange(181.0)
    cos = np.cos(np.radians(angles))
    weight = np.where(angles <= FORWARD, FORWARD_WEIGHT, 1.0)

    def shares(p):
        # The second's share is of what the first leaves, so that the two never pass 1.
        return p[2], (1 - p[2]) * p[3]

    def residuals(p):
        return weight * np.log(scattering.phase_function(cos, p[0], p[1], *shares(p)) / phase)

    best = min((optimize.least_squares(residuals, start, bounds=(LOWEST, HIGHEST)) for start in FIRST_GUESSES), key=lambda fit: fit.cost)
    return best.x[0], best.x[1], *shares(best.x)


if __name__ == '__main__':
    data = sys.argv[1]
    with open(os.path.join(data, 'colour.json')) as f:
        colours = json.load(f)['colours']
    names = sorted(photometry.HAZE, key=photometry.HAZE.get)
    extinction, albedo, fitted = [], [], []
    for name in names:
        wavelength = photometry.HAZE[name]
        parts = [(number, *droplets(radius, VARIANCE, wavelength)) for radius, number in MODES]
        # Per km: a number a cubic centimetre times a cross-section in square micrometres is 1e-8 per
        # cm, 1e-3 per km.
        total = sum(number * each for number, each, _, _ in parts) * 1e-3
        scattered = sum(number * each for number, _, each, _ in parts) * 1e-3
        phase = sum(number * each * p for number, _, each, p in parts) * 1e-3 / scattered
        first, second, first_share, second_share = lobes(phase)
        extinction.append(total)
        albedo.append(scattered / total)
        fitted.append((first, second, first_share, second_share))
        print(f"{name}, {wavelength:.0f} nm: extinction at 75 km {total:.4g} per km, the small droplets "
              f"{parts[0][0] * parts[0][1] * 1e-3 / total:.0%} of it; albedo {scattered / total:.6f}; lobes {first:.3f} and "
              f"{second:.3f}, with {first_share:.3f} and {second_share:.3f} of the light; light scattered by 5, 30, 90 and 150 "
              "degrees, " + ', '.join(f"{phase[a]:.3g}" for a in (5, 30, 90, 150)))
    first, second, first_share, second_share = np.array(fitted).T
    print('for venus.glsl:')
    print(scattering.constructor(
        'venusHaze', UNIT, UNIT + REFERENCE, UNIT + TOP, extinction, [SCALE] * 3, [0.0] * 3, [UNIT] * 3, [1.0] * 3,
        -np.cos(np.radians(photometry.PHASE)), albedo, first, second, first_share, second_share, None, [colours[name] for name in names],
        BLOOM))
