"""Composes Jupiter's texture from Cassini's map of December 2000, calibrated with Hubble's maps of
January 2015, as a 4096x2048 sRGB PNG: north at the top and east to the right, as `sphere.py`'s
spheres map it, with the longitudes of Cassini's map.

    python3 compose.py data data/1993.tab out.png <stretch> <brightness>

- Cassini's cylindrical map (PIA07782) has 0.1 degrees a pixel, in planetocentric latitude and
  longitude. It holds data from 88 degrees north to 82 south. Past that, Cassini saw nothing, and the
  map holds one flat colour. The last degrees of data fade into their own mean colour, which fills the
  two small caps.
- Cassini's published map has its contrast stretched, as pictures of Jupiter usually are. Hubble's
  OPAL maps are calibrated: I/F, with the limb darkening taken out by Minnaert's law. So each
  channel's contrast is brought down to Jupiter's own at the channel's wavelength, measured as the
  spread of the logarithm of the brightness between its 10th and 90th percentiles, from 60 degrees
  south to 60 north, and interpolated between OPAL's filters at 395, 502 and 631 nm.
- Cassini made the colour from two filters, blue at 451 nm and near-infrared at 750 nm. So the map
  keeps its own variations, but its mean colour is set to that of Karkoschka's spectrum of Jupiter
  (`truecolour.py`).
- `stretch` multiplies Jupiter's contrast, on the logarithm of the brightness, for the game: 1 keeps
  Jupiter's own. `brightness` is the texture's mean luminance in linear light, for the game: at its
  true normal albedo, about 0.78, Jupiter is near white in the game's lighting.
- The texture holds the body's own colour, as the mod lights the planets with white light
  (`records.planet_light` in `records.luau`). If its brightest texels pass 1, the whole map is scaled
  down until all but `CLIPPED` of them fit.
- For `haze.py`, it writes what an I/F of 1 at each of the haze's wavelengths becomes in the
  texture's linear sRGB, as the texture takes a place's albedo there, to `data/colour.json`.
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import fits  # noqa: E402
import scattering  # noqa: E402
import truecolour as tc  # noqa: E402

data, spectrum, out = sys.argv[1], sys.argv[2], sys.argv[3]
stretch, brightness = float(sys.argv[4]), float(sys.argv[5])

# Jupiter's radii, km (IAU), for turning OPAL's planetographic latitudes into planetocentric ones.
EQUATOR, POLE = 71492.0, 66854.0
# Cassini's map's degrees a pixel.
STEP = 0.1
# How many degrees before the end of Cassini's data its detail fades into the caps' colour, and how
# many degrees of data that colour is the mean of.
FADE = 3.0
CAP_MEAN = 2.0
# OPAL's maps of January 2015 (rotation A): each filter's wavelength, nm, and the factor that turns
# its values into I/F, from the maps' readme.
OPAL = {'f395n': (395.0, 0.00475), 'f502n': (502.0, 0.00499), 'f631n': (631.0, 0.00535)}
# The latitudes the contrast is measured over, planetographic, and its percentiles.
CONTRAST_LATITUDE = 60.0
PERCENTILES = (0.1, 0.9)
# The share of texels allowed past 1, and so clipped, if the map has to be scaled down to fit.
CLIPPED = 0.001
SIZE = (4096, 2048)


def centric(graphic):
    """Planetocentric latitudes from planetographic ones, degrees."""
    return np.degrees(np.arctan(np.tan(np.radians(graphic)) * (POLE / EQUATOR) ** 2))


def spread(values, weights):
    """How far apart the logarithms of `values` lie between the percentiles, weighted by area."""
    order = np.argsort(values)
    logs, cumulative = np.log(values[order]), np.cumsum(weights[order])
    cumulative /= cumulative[-1]
    low, high = PERCENTILES
    return np.interp(high, cumulative, logs) - np.interp(low, cumulative, logs)


# Cassini's map in linear light: rows from 90 north to 90 south, and columns east from its left edge.
# Its last column repeats its first.
source = f"{data}/PIA07782.tif"
w, h = map(int, subprocess.run(['magick', 'identify', '-format', '%w %h', source], capture_output=True, text=True,
                               check=True).stdout.split())
raw = subprocess.run(['magick', source, '-colorspace', 'RGB', '-depth', '16', 'rgb:-'], capture_output=True, check=True).stdout
texture = (np.frombuffer(raw, '<u2').reshape(h, w, 3).astype(np.float64) / 65535)[:, :-1]
lats = 90 - np.arange(texture.shape[0]) * STEP
area = np.broadcast_to(np.cos(np.radians(lats))[:, None], texture.shape[:2])
# Past the data, rows hold one flat colour.
flat = texture.std(axis=1).max(axis=1) < 1e-6
for north in (True, False):
    side = lats > 0 if north else lats < 0
    data_rows = side & ~flat
    last = np.abs(lats[data_rows]).max()
    colour = texture[data_rows & (np.abs(lats) >= last - CAP_MEAN)].mean(axis=(0, 1))
    t = np.clip((np.abs(lats) - (last - FADE)) / FADE, 0, 1)
    weight = np.where(side, t * t * (3 - 2 * t), 0.0)[:, None, None]
    texture = texture * (1 - weight) + colour * weight
    print(f"{'north' if north else 'south'}: Cassini's data to {last:.1f} degrees, the cap filled with linear sRGB {np.round(colour, 3)}")

# OPAL: each filter's contrast and mean normal albedo. Its maps hold rows from north to south at 10 a
# degree, in planetographic latitude, and nothing (zero) past 79.8 degrees.
opal_lats = 90 - (np.arange(1800) + 0.5) * 0.1
opal_area = np.cos(np.radians(centric(opal_lats)))[:, None]
measured = {}
for name, (wavelength, factor) in OPAL.items():
    path = f"{data}/hlsp_opal_hst_wfc3-uvis_jupiter-2015a_{name}_v1_globalmap.fits"
    reflectance = fits.image(path) * factor
    seen = reflectance > 0
    band = seen & (np.abs(opal_lats) <= CONTRAST_LATITUDE)[:, None]
    cells = np.broadcast_to(opal_area, reflectance.shape)
    normal = (reflectance * cells)[seen].sum() / cells[seen].sum()
    measured[wavelength] = (spread(reflectance[band], cells[band]), normal)
    print(f"OPAL {name}: contrast {np.exp(measured[wavelength][0]):.3f} from the 10th to the 90th percentile, mean normal albedo {normal:.3f}")
wavelengths = sorted(measured)

# Each channel's wavelength, for Jupiter's spectrum: the mean of the wavelengths it takes in.
lam, albedo = tc.karkoschka(spectrum, 'jupiter')
weights = tc.matrix(lam)
channel = tc.channels(lam, albedo, weights)

# Each channel's contrast brought to Jupiter's own, about its geometric mean.
band = np.abs(lats) <= centric(CONTRAST_LATITUDE)
for c in range(3):
    target = stretch * np.interp(channel[c], wavelengths, [measured[l][0] for l in wavelengths])
    values = texture[band][..., c].ravel()
    exponent = target / spread(values, area[band].ravel())
    pivot = np.exp(np.sum(np.log(values) * area[band].ravel()) / area[band].sum())
    texture[..., c] = pivot * (texture[..., c] / pivot) ** exponent
    print(f"{'RGB'[c]} at {channel[c]:.0f} nm: contrast {np.exp(target):.3f}, Cassini's map's scaled by {exponent:.3f}")

# The mean colour, over the area of the planet, set to the spectrum's, at the brightness asked for.
green = channel[1]
normal_over_geometric = np.interp(green, wavelengths, [measured[l][1] / np.interp(l, lam, albedo) for l in wavelengths])
geometric = (albedo[:, None] * weights).sum(axis=0)
mean = (texture * area[..., None]).sum(axis=(0, 1)) / area.sum()
texture *= geometric / mean * brightness / tc.luminance(geometric)
print(f"geometric albedo, linear sRGB {np.round(geometric, 4)}, as 8-bit sRGB {np.round(tc.encode(geometric) * 255).astype(int)}; "
      f"true mean luminance at the normal albedo, {normal_over_geometric:.3f} times the geometric: "
      f"{normal_over_geometric * tc.luminance(geometric):.3f}; in the texture: {brightness:.3f}")
fit = max(1.0, np.quantile(texture, 1 - CLIPPED))
texture /= fit
print(f"scaled down by {fit:.3f} to fit")

# Resampled to the texture's grid, each texel's middle at its latitude and longitude, in linear light.
w, h = SIZE
pad = 4
padded = np.concatenate([texture[:, -pad:], texture, texture[:, :pad]], axis=1)
row = (np.arange(h) + 0.5) * 180 / h / STEP
column = (np.arange(w) + 0.5) * 360 / w / STEP + pad
rr, cc = np.meshgrid(row, column, indexing='ij')
img = np.stack([ndimage.map_coordinates(padded[..., c], [rr, cc], order=3, mode='nearest') for c in range(3)], axis=-1)
pixels = (np.clip(img, 0, 1) * 65535 + 0.5).astype('<u2')
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '16', '-endian', 'LSB', 'rgb:-', '-set', 'colorspace', 'RGB',
                '-colorspace', 'sRGB', '-depth', '8', '-define', 'png:exclude-chunks=date,time', out],
               input=pixels.tobytes(), check=True)
print('wrote', out)

# For haze.py: an I/F of 1 at each of the haze's wavelengths in the texture's linear sRGB, as a place
# whose albedo there is the spectrum's adds that wavelength's share of the spectrum, at the texture's
# scale.
scale = brightness / tc.luminance(geometric)
colours = {name: (scale / fit * each).tolist()
           for name, each in zip(scattering.WAVELENGTHS, tc.filter_colours(lam, albedo, weights, list(scattering.WAVELENGTHS.values())))}
with open(os.path.join(data, 'colour.json'), 'w') as f:
    json.dump({'about': "Jupiter's I/F at each of the haze's wavelengths as the texture's linear sRGB: a row for each "
                        "wavelength.", 'colours': colours}, f, indent=1)
print("the texture's linear sRGB for an I/F of 1 at each wavelength:", {name: np.round(c, 5).tolist() for name, c in colours.items()})
