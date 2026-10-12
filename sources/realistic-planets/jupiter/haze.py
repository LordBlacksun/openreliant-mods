"""Works out Jupiter's stratospheric haze for the mod's `jupiter.glsl` from what was measured of it,
and prints the shader's numbers. Run `compose.py` first: it writes `data/colour.json`, which turns
the haze's I/F into the texture's colours.

    python3 haze.py data

Cassini saw Jupiter at high phase only from 18 million km, at about 110 km a pixel, and Galileo's
frames of its limb at high phase are kept raw and compressed with loss, so the haze isn't fitted to
frames of the limb, as Titan's, Neptune's and Saturn's are. It's built from what was measured of it:

- From the equator to the middle latitudes, the stratospheric haze is a layer near 50 mbar of compact
  particles with radii of 0.2 to 0.5 micrometres (Zhang and others, 2013), whose optical depth is
  about a tenth in the near infrared (Banfield and others, 1998). The particles here have an effective
  radius of 0.3 micrometres and spread as a log-normal of effective variance `VARIANCE` (`PARTICLES`),
  with the refractive index of a hydrocarbon haze, about 1.5, absorbing next to no visible light
  (`INDEX`). The haze over the poles, of larger aggregates, is left out.
- Mie theory (`mie.py`) gives the particles' cross-section and phase function at 756 nm, where the
  optical depth is given, and at each of the haze's wavelengths (`scattering.WAVELENGTHS`): the
  haze's extinction there is the optical depth's, scaled by the cross-section.
- The haze mixes with the gas, so its extinction falls exponentially with the gas's scale height near
  50 mbar, about 19 km at 125 K (`SCALE`), and the optical depth is the haze's above 50 mbar, about
  70 km above the 1-bar level (`REFERENCE`). Followed down to that level, the same haze reaches an
  optical depth of about 3, as the upper troposphere's haze does.
- The model's phase function, two Henyey-Greenstein lobes and Rayleigh's, is fitted to the particles'
  (`mie.lobes`).

The game's spheroid is Jupiter's 1-bar level, flattened along its pole (`UNIT`, `POLAR`). The light
the haze scatters more than once isn't estimated, as for Saturn's.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import mie  # noqa: E402
import scattering  # noqa: E402

# Jupiter's equatorial and polar radii at 1 bar, km (IAU): the game's spheroid.
UNIT = 71492.0
POLAR = 66854.0
# The height the extinction is given at, km above `UNIT`, about where 50 mbar lies, and the height
# the haze is cut off at, where its extinction is a hundred-millionth of the reference's or less.
REFERENCE = 70.0
TOP = 420.0
# The haze's particles: their effective radius, micrometres, and effective variance; their refractive
# index; the optical depth above `REFERENCE` at `DEPTH_AT` nm; and the scale height, km.
PARTICLES = 0.3
VARIANCE = 0.1
INDEX = 1.5 + 0j
DEPTH = 0.1
DEPTH_AT = 756.0
SCALE = 19.0
# How much of the haze's light blooms, which the mod chooses rather than the fit: a quarter, as for
# the other bodies.
BLOOM = 0.25


if __name__ == '__main__':
    data = sys.argv[1]
    with open(os.path.join(data, 'colour.json')) as f:
        colours = json.load(f)['colours']
    names = list(scattering.WAVELENGTHS)
    # The particles' number at `REFERENCE`, in units that make it times a cross-section, in square
    # micrometres, the extinction per km: what gives the optical depth `DEPTH` at `DEPTH_AT`.
    reference, _, _ = mie.particles(PARTICLES, VARIANCE, INDEX, DEPTH_AT)
    number = DEPTH / SCALE / reference
    extinction, albedo, fitted = [], [], []
    for name in names:
        wavelength = scattering.WAVELENGTHS[name]
        total, scattered, phase = mie.particles(PARTICLES, VARIANCE, INDEX, wavelength)
        first, second, first_share, second_share = mie.lobes(phase)
        extinction.append(number * total)
        albedo.append(scattered / total)
        fitted.append((first, second, first_share, second_share))
        print(f"{name}, {wavelength:.0f} nm: extinction at 50 mbar {number * total:.4g} per km, {total / reference:.2f} times "
              f"{DEPTH_AT:.0f} nm's; albedo {scattered / total:.6f}; lobes {first:.3f} and {second:.3f}, with {first_share:.3f} "
              f"and {second_share:.3f} of the light; light scattered by 5, 30, 90 and 150 degrees, "
              + ', '.join(f"{phase[a]:.3g}" for a in (5, 30, 90, 150)))
    first, second, first_share, second_share = np.array(fitted).T
    print('for jupiter.glsl:')
    # The texture's phase: Hubble's and Cassini's maps take the light's angle out, so it shows Jupiter
    # as from the sun.
    print(scattering.constructor(
        'jupiterHaze', UNIT, UNIT + REFERENCE, UNIT + TOP, extinction, [SCALE] * 3, [0.0] * 3, [UNIT] * 3, [1.0] * 3, -1.0,
        albedo, first, second, first_share, second_share, None, [colours[name] for name in names], BLOOM, polar=POLAR / UNIT))
