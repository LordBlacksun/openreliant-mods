"""Measures how Venus's limb darkens in the game's red, green and blue, for the mod's limb function in
`planets.luau`, from pictures by Venus Express's camera, VMC.

    python3 limb.py data

- VMC took pictures of Venus at 365, 513 and 965 nm within a minute of each other. A geometry file
  beside each picture holds each pixel's latitude and the angles of the light and the view. The
  frames used here are six such sets from July and August 2007, taken from 22,000 to 34,000 km away
  at phase angles of 44 to 55 degrees.
- Each frame's Minnaert exponent is fitted as for Akatsuki's maps (`photometry.minnaert`), each degree
  of latitude with its own brightness, where the sun is more than `LEAST_HEIGHT` degrees up and the
  view more than that above the limb. Each band's exponent is the mean of its frames'.
- Each channel's exponent is the one at its wavelength for Venus's spectrum (`photometry.channels`),
  interpolated along the wavelength between the bands' exponents.
"""
import glob
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import photometry  # noqa: E402
import truecolour as tc  # noqa: E402

data = sys.argv[1]

# VMC's bands, by the detector's name in the file names, and the wavelength each filter centres on, nm
# (Markiewicz et al. 2007).
WAVELENGTHS = {'UV2': 365.0, 'VI2': 513.0, 'N12': 965.0}
# The least height of the sun, and of the view above the limb, where a frame is used, degrees.
LEAST_HEIGHT = 15.0


def read(path):
    """A PDS3 image's bands, as floating point numbers, and its label's text."""
    with open(path, 'rb') as f:
        text = f.read(65536).decode('latin-1')

    def value(key):
        return re.search(r'^\s*' + re.escape(key) + r'\s*=\s*([^\r\n<]+)', text, re.M).group(1).strip().strip('"')
    record, start = int(value('RECORD_BYTES')), int(value('^IMAGE'))
    lines, samples = int(value('LINES')), int(value('LINE_SAMPLES'))
    bands = int(value('BANDS')) if re.search(r'^\s*BANDS\s*=', text, re.M) else 1
    dtype = {'MSB_INTEGER': '>i2', 'IEEE_REAL': '>f4'}[value('SAMPLE_TYPE')]
    image = np.fromfile(path, dtype=dtype, count=lines * samples * bands, offset=(start - 1) * record)
    return image.reshape(bands, lines, samples).astype(np.float64), value


# Each frame's exponent.
fitted = {band: [] for band in WAVELENGTHS}
least = np.sin(np.radians(LEAST_HEIGHT))
for path in sorted(glob.glob(f"{data}/V*_*.IMG")):
    band = os.path.basename(path)[11:14]
    if band not in WAVELENGTHS:
        continue
    counts, value = read(path)
    (incidence, emission, phase, latitude, _), _ = read(path[:-4] + '.GEO')
    radiance = counts[0] * float(value('RADIANCE_SCALING_FACTOR')) + float(value('RADIANCE_OFFSET'))
    mu0, mu = np.cos(np.radians(incidence)), np.cos(np.radians(emission))
    good = (radiance > 0) & (mu0 > least) & (mu > least) & (np.abs(latitude) <= 90)
    k = photometry.minnaert(radiance, mu0, mu, good, np.floor(np.where(good, latitude, 0) + 90).astype(int))
    fitted[band].append(k)
    print(f"{os.path.basename(path)} at {value('IMAGE_TIME')}, {WAVELENGTHS[band]:.0f} nm: phase angle "
          f"{np.median(phase[good]):.0f} degrees, Minnaert's exponent {k:.3f}")
bands = sorted(WAVELENGTHS, key=WAVELENGTHS.get)
exponents = [np.mean(fitted[band]) for band in bands]
print("each band's exponent: " + ", ".join(f"{e:.3f} at {WAVELENGTHS[b]:.0f} nm" for b, e in zip(bands, exponents)))

# Each channel's exponent, at its wavelength for Venus's spectrum.
lam = np.arange(380.0, 781.0, 1.0)
points, values = photometry.spectrum()
channels = photometry.channels(lam, np.interp(lam, points, values), tc.matrix(lam))
limb = np.interp(channels, [WAVELENGTHS[b] for b in bands], exponents)
print(f"the channels' wavelengths for Venus's spectrum: {np.round(channels).astype(int)} nm; their exponents, for planets.luau: "
      f"{np.round(limb, 3)}; the limb's brightness where mu is 0.25, against a plain ball's: {np.round(0.25 ** (limb - 1), 3)}")
