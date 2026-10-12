"""Composes Neptune's texture from the mosaics, as a 4096x2048 sRGB PNG: north at the top, 0 degrees
east in the middle column and east to the right, as `sphere.py`'s spheres map it.

    python3 compose.py maps data/1993.tab out.png <enhance>

- The brightness is the luminance mosaic's, at Neptune's normal albedo: the spectrum's full-disk
  albedo, scaled by the green mosaic's Minnaert albedo over the spectrum's in green.
- The colour is true colour (`truecolour.py`) of Karkoschka's albedo spectrum of Neptune, bent at
  each place through the blue, green and orange mosaics' ratios to their means, at 479, 566 and
  591 nm, and smoothed over 2 degrees, as the colour frames are three days older and their single
  clouds have moved otherwise than the winds.
- Past 32 degrees north every frame saw the clouds near its limb, and the data ends between 37 and
  47 north. From 32 to 40 north the map blends into the southern hemisphere's bands at the same
  latitude, smoothed along each latitude so that no cloud shows twice.
- `enhance` multiplies the brightness's differences from the mean, as Voyager's published images
  of Neptune were stretched; 1 keeps true colour, and the mean colour stays true either way.
- The texture holds Neptune's own colour, as the mod lights the planets with white light
  (`records.planet_light` in `records.luau`).
- For `haze.py`, it writes what an I/F of 1 in each of the blue, green and orange filters becomes in
  the texture's linear sRGB, as the texture takes a place's albedo in them, to `data/colour.json`.
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import truecolour as tc  # noqa: E402
import voyager  # noqa: E402

maps, spectrum, out = sys.argv[1], sys.argv[2], sys.argv[3]
enhance = float(sys.argv[4])

lum = np.load(f"{maps}/luminance.npz")
L, lats, lons = lum['albedo'], lum['lats'], lum['lons']
colour = {f: np.load(f"{maps}/{f}.npz") for f in ('Blue', 'Green', 'Orange')}
clats = colour['Green']['lats']
cstep = clats[1] - clats[0]
step = lats[1] - lats[0]


def on_luminance_grid(a):
    """A colour mosaic resampled onto the luminance mosaic's finer grid, wrapping in longitude."""
    rr, cc = np.meshgrid((lats + 90) / cstep - 0.5, lons / cstep - 0.5, indexing='ij')
    padded = np.concatenate([a[:, -1:], a, a[:, :1]], axis=1)
    return ndimage.map_coordinates(padded, [rr, cc + 1], order=1, mode='nearest')


# Each filter's map relative to its mean over the well-seen latitudes, smoothed.
seen = (clats > -60) & (clats < 20)
ratio = {f: on_luminance_grid(voyager.smooth(m['albedo'] / np.nanmean(m['albedo'][seen]), 2.0, cstep)) for f, m in colour.items()}

# The spectrum, bent through each filter by hat functions that sum to one: blue at 479 nm, green at
# 566, orange at 591, flat beyond them.
lam, ref = tc.karkoschka(spectrum, 'neptune')
M = tc.matrix(lam)
hats = dict(zip(('Blue', 'Green', 'Orange'), tc.hats(lam, [479.0, 566.0, 591.0])))
K = {f: ((ref * h)[:, None] * M).sum(axis=0) for f, h in hats.items()}
mean_rgb = sum(K.values())


def luminance(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


print('mean colour, linear', np.round(mean_rgb, 4), 'sRGB', np.round(tc.encode(mean_rgb) * 255).astype(int))
rgb = sum(np.nan_to_num(ratio[f], nan=1.0)[..., None] * K[f] for f in K)
chroma = rgb / luminance(rgb)[..., None]

green = np.exp(-0.5 * ((lam - 566) / 17) ** 2)
normal_over_full = np.nanmean(colour['Green']['albedo'][seen]) / (np.sum(ref * green) / np.sum(green))
print(f"normal albedo over the spectrum's geometric albedo, in green: {normal_over_full:.3f}")
relative = L / np.nanmean(L[(lats > -60) & (lats < 20)])

# The far north.
mirror = voyager.smooth(relative[::-1], 0.3, step)
mirror = ndimage.uniform_filter1d(np.nan_to_num(mirror, nan=1.0), size=int(round(45 / step)), axis=1, mode='wrap')
blend = np.clip((lats[:, None] - 32.0) / 8.0, 0, 1) * np.ones((1, relative.shape[1]))
blend = blend * blend * (3 - 2 * blend)
filled = np.where(np.isfinite(relative), relative * (1 - blend) + mirror * blend, mirror)
chroma = chroma * (1 - blend[..., None]) + chroma[::-1] * blend[..., None]

stretched = np.clip(1.0 + enhance * (filled - 1.0), 0.05, None)
linear = chroma * (luminance(mean_rgb) * normal_over_full * stretched)[..., None]

# For haze.py: an I/F of 1 in each filter in the texture's linear sRGB, as a place whose albedo in a
# filter is its mean's adds that filter's share of the spectrum.
colours = {f: (K[f] * normal_over_full / np.nanmean(m['albedo'][seen])).tolist() for f, m in colour.items()}
with open(os.path.join(os.path.dirname(spectrum), 'colour.json'), 'w') as f:
    json.dump({'about': "Neptune's I/F in each of Voyager's filters as the texture's linear sRGB: a row for each "
                        "filter.", 'colours': colours}, f, indent=1)
print('the texture\'s linear sRGB for an I/F of 1 in each filter:', {f: np.round(c, 5).tolist() for f, c in colours.items()})

# North at the top and 180 east at the left edge, resampled to 4096x2048 in linear light.
img = np.clip(np.roll(linear[::-1], linear.shape[1] // 2, axis=1), 0, 1).astype(np.float32)
h, w = img.shape[:2]
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '32', '-define', 'quantum:format=floating-point', '-endian', 'LSB',
                'rgb:-', '-set', 'colorspace', 'RGB', '-virtual-pixel', 'HorizontalTileEdge', '-filter', 'Lanczos',
                '-distort', 'Resize', '4096x2048!', '-colorspace', 'sRGB', '-depth', '8', '-define', 'png:exclude-chunks=date,time', out],
               input=img.tobytes(), check=True)
print('wrote', out)
