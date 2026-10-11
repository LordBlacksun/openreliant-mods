"""Composes Uranus's texture from Hubble's OPAL maps of November 2022, as a 4096x2048 sRGB PNG: north
at the top and east to the right, as `sphere.py`'s spheres map it.

    python3 compose.py data data/1993.tab out.png <stretch> <brightness> <key light blue>

- OPAL's maps are calibrated: I/F, with the limb darkening taken out by Minnaert's law, at 0.5
  degrees a pixel in planetographic latitude. Their files hold the north first and put 0 degrees east
  at the right edge, east increasing to the left, as their readme says, so the texture reverses their
  columns to put east to the right, as seen from outside, with 0 degrees east in the middle column.
- Hubble sees Uranus's north, which faces the sun, down to about 30 degrees south, but past about 5
  degrees south the maps grow noisy, seen near the limb. The data is trusted where the brightness
  varies from one pixel to the next along a latitude by less than `ROUGH` in every map. Past that,
  the map takes the northern hemisphere's bands at the same latitude, averaged along each latitude so
  that no cloud shows twice, blended in over `FILL` degrees before the trusted data ends. It is a
  plausible guess, not data: Voyager 2 saw a bright south polar cap in 1986, as Hubble sees a
  northern one now.
- The colour is true colour (`truecolour.py`) of Karkoschka's albedo spectrum of Uranus, bent at
  each place through the 467, 547 and 657 nm maps' ratios to their means. `stretch` multiplies the
  contrast of the luminance alone, on its logarithm, for the game, keeping each place's colour: 1
  keeps Uranus's own. Stretching each map instead would turn the polar cap pink, as nearly all of
  Uranus's contrast is in the red map.
- `brightness` is the texture's mean luminance in linear light, for the game: at its true normal
  albedo, the spectrum's geometric albedo times the ratio of OPAL's mean normal albedo to it at 547 nm,
  about 0.61, Uranus is washed out in the game's lighting.
- `key light blue` is the blue of the only light that reaches a planet in StarLancer, (1, 1, 0.8):
  the texture's blue is divided by it, so that the planet shows its own colour in the game. If that
  takes the brightest texels past 1, the whole map is scaled down until all but `CLIPPED` of them fit.
"""
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import fits  # noqa: E402
import truecolour as tc  # noqa: E402

data, spectrum, out = sys.argv[1], sys.argv[2], sys.argv[3]
stretch, brightness, key_blue = float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6])

# Uranus's radii, km (IAU), for turning planetographic latitudes into planetocentric ones.
EQUATOR, POLE = 25559.0, 24973.0
# OPAL's maps of November 2022 (rotation A): each filter's wavelength, nm, and the factor that turns
# its values into I/F, from the maps' readme.
OPAL = {'f467m': (467.0, 0.00320), 'f547m': (547.0, 0.00254), 'f657n': (657.0, 0.00447)}
# The maps' degrees a pixel.
STEP = 0.5
# The latitudes the filters' means are taken over, and how many degrees before the end of the data the
# southern fill blends in, and how wide the average along each latitude is, degrees.
MEAN_LATITUDES = (-20.0, 60.0)
FILL = 10.0
ALONG = 45.0
ROUGH = 0.01
# The share of texels allowed past 1, and so clipped, if the map has to be scaled down to fit.
CLIPPED = 0.001
SIZE = (4096, 2048)


def centric(graphic):
    """Planetocentric latitudes from planetographic ones, degrees."""
    return np.degrees(np.arctan(np.tan(np.radians(graphic)) * (POLE / EQUATOR) ** 2))


def graphic(centric_lat):
    """Planetographic latitudes from planetocentric ones, degrees."""
    return np.degrees(np.arctan(np.tan(np.radians(centric_lat)) / (POLE / EQUATOR) ** 2))


def row_means(m):
    """Each row's mean over the cells that hold data, or NaN for a row with none."""
    seen = np.isfinite(m)
    count = seen.sum(axis=1, keepdims=True)
    total = np.where(seen, m, 0).sum(axis=1, keepdims=True)
    return np.where(count > 0, total / np.maximum(count, 1), np.nan)


def area_mean(m, rows):
    """The mean of `m` over `rows`, weighted by area."""
    weights = np.broadcast_to(area[rows], m[rows].shape)
    return np.sum(m[rows] * weights) / np.sum(weights)


# Each map as I/F: rows from 90 north to 90 south, columns east from 0 degrees, the last column, which
# repeats the first, left out.
maps = {}
for name, (wavelength, factor) in OPAL.items():
    image = fits.image(f"{data}/hlsp_opal_hst_wfc3-uvis_uranus-2022a_{name}_v1_globalmap.fits")[:, ::-1][:, :-1]
    maps[wavelength] = np.where(image > 0, image * factor, np.nan)
wavelengths = sorted(maps)
lats = 90 - np.arange(next(iter(maps.values())).shape[0]) * STEP
area = np.cos(np.radians(centric(lats)))[:, None]

# Past the data, the northern hemisphere's bands at the same latitude, averaged along each latitude.

def roughness(m):
    """How much the brightness varies from one pixel to the next along each row, over the row's mean."""
    steps = np.diff(m, axis=1)
    spread = np.sqrt(np.maximum(row_means(steps * steps) - row_means(steps) ** 2, 0))
    return (spread / row_means(m))[:, 0]


rough = np.max([roughness(m) for m in maps.values()], axis=0)
trusted = np.isfinite(rough) & (rough < ROUGH)
last = lats[np.nonzero(~trusted)[0][0]] + STEP
print(f"data trusted from the north pole to {last:.1f} degrees")
t = np.clip(((last + FILL) - lats) / FILL, 0, 1)
blend = (t * t * (3 - 2 * t))[:, None]
for wavelength, m in maps.items():
    mirror = m[::-1]
    mirror = np.where(np.isfinite(mirror), mirror, row_means(mirror))
    mirror = ndimage.uniform_filter1d(mirror, size=int(round(ALONG / STEP)), axis=1, mode='wrap')
    filled = np.where(blend > 0, m * (1 - blend) + mirror * blend, m)
    maps[wavelength] = np.where(np.isfinite(m), filled, mirror)

# Each map's ratio to its mean.
band = (lats >= MEAN_LATITUDES[0]) & (lats <= MEAN_LATITUDES[1])
ratio = {}
everywhere = np.ones_like(lats, dtype=bool)
for wavelength, m in maps.items():
    r = m / area_mean(m, band)
    ratio[wavelength] = r / area_mean(r, everywhere)
    print(f"{wavelength:.0f} nm: mean normal albedo {area_mean(m, band):.3f}, contrast from the 10th to the 90th "
          f"percentile {np.percentile(m[band], 90) / np.percentile(m[band], 10):.3f}")

# The spectrum bent through each filter by hat functions that sum to one, flat beyond them.
lam, albedo = tc.karkoschka(spectrum, 'uranus')
M = tc.matrix(lam)
blue, green, red = wavelengths
hat_b = np.interp(lam, [blue, green], [1, 0])
hat_r = np.interp(lam, [green, red], [0, 1])
hats = {blue: hat_b, green: 1 - hat_b - hat_r, red: hat_r}
K = {w: ((albedo * h)[:, None] * M).sum(axis=0) for w, h in hats.items()}
geometric = sum(K.values())
texture = sum(ratio[w][..., None] * K[w] for w in wavelengths)
# The luminance's contrast stretched on its logarithm, each place keeping its colour.
luminance = tc.luminance(texture)
mean = area_mean(luminance, everywhere)
texture *= ((luminance / mean) ** (stretch - 1))[..., None]
texture *= mean / area_mean(tc.luminance(texture), everywhere)

# At the brightness asked for; the true normal albedo, measured at the green filter, for reference.
normal_over_geometric = area_mean(maps[green], band) / np.interp(green, lam, albedo)
texture *= brightness / area_mean(tc.luminance(texture), everywhere)
print(f"geometric albedo, linear sRGB {np.round(geometric, 4)}, as 8-bit sRGB {np.round(tc.encode(geometric) * 255).astype(int)}; "
      f"true mean luminance at the normal albedo, {normal_over_geometric:.3f} times the geometric: "
      f"{normal_over_geometric * tc.luminance(geometric):.3f}; in the texture: {brightness:.3f}")
texture[..., 2] /= key_blue
fit = max(1.0, np.quantile(texture, 1 - CLIPPED))
texture /= fit
print(f"scaled down by {fit:.3f} to fit")

# Resampled to the texture's grid, each texel's middle at its planetocentric latitude and longitude,
# 0 degrees east in the middle column, in linear light.
w, h = SIZE
pad = 4
padded = np.concatenate([texture[:, -pad:], texture, texture[:, :pad]], axis=1)
row = (90 - graphic(90 - (np.arange(h) + 0.5) * 180 / h)) / STEP
column = ((np.arange(w) + 0.5) * 360 / w - 180) % 360 / STEP + pad
rr, cc = np.meshgrid(row, column, indexing='ij')
img = np.stack([ndimage.map_coordinates(padded[..., c], [rr, cc], order=3, mode='nearest') for c in range(3)], axis=-1)
pixels = (np.clip(img, 0, 1) * 65535 + 0.5).astype('<u2')
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '16', '-endian', 'LSB', 'rgb:-', '-set', 'colorspace', 'RGB',
                '-colorspace', 'sRGB', '-depth', '8', '-define', 'png:exclude-chunks=date,time', out],
               input=pixels.tobytes(), check=True)
print('wrote', out)
