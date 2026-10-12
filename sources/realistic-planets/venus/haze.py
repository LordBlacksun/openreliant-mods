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
- Mie theory (`mie.py`) gives each size's cross-section and phase function at each of the haze's
  wavelengths (`scattering.WAVELENGTHS`). The haze's extinction at 75 km is the droplets' number
  times their cross-section, and its single-scattering albedo the droplets'.
- The extinction falls exponentially above, with the aerosol scale height SPICAV IR measured, 3.3
  km (`SCALE`).
- The model's phase function, two Henyey-Greenstein lobes and Rayleigh's for the rest of the light,
  is fitted to the droplets' (`mie.lobes`): it follows their forward peak within about 10%, and the
  rest within about 20 to 30%, short of their glory near the backward direction.

The game's sphere is Venus's cloud tops, about 70 km up, which Akatsuki's maps in the texture show
(`UNIT`). The light the haze scatters more than once isn't estimated, as for Saturn's.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mie  # noqa: E402
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
INDEX = {450.0: 1.45 + 0j, 550.0: 1.44 + 0j, 650.0: 1.43 + 0j}
# The aerosol scale height, km.
SCALE = 3.3
# How much of the haze's light blooms, which the mod chooses rather than the fit: a quarter, as for
# the other bodies.
BLOOM = 0.25


if __name__ == '__main__':
    data = sys.argv[1]
    with open(os.path.join(data, 'colour.json')) as f:
        colours = json.load(f)['colours']
    names = list(scattering.WAVELENGTHS)
    extinction, albedo, fitted = [], [], []
    for name in names:
        wavelength = scattering.WAVELENGTHS[name]
        parts = [(number, *mie.particles(radius, VARIANCE, INDEX[wavelength], wavelength)) for radius, number in MODES]
        # Per km: a number a cubic centimetre times a cross-section in square micrometres is 1e-8 per
        # cm, 1e-3 per km.
        total = sum(number * each for number, each, _, _ in parts) * 1e-3
        scattered = sum(number * each for number, _, each, _ in parts) * 1e-3
        phase = sum(number * each * p for number, _, each, p in parts) * 1e-3 / scattered
        first, second, first_share, second_share = mie.lobes(phase)
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
