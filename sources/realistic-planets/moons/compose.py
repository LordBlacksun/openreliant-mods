"""Composes a moon's texture, one of Jupiter's or Triton, `width` wide and half as high: north at the
top and east to the right, as `sphere.py`'s spheres map it, with 0 degrees east in the middle column.
Its detail comes from a global map of the moon, and its colour from Voyager's frames. It also prints
the limb's exponents for the mod's `planets.luau`.

    python3 compose.py data frames.json fits.json <moon> out.png <width> <brightness> <key light blue>

- Each frame's pointing is fitted by `fit.py`, and its sky is taken off it (`moons.sky`). Each
  filter's Minnaert exponent is the median of its frames': Io's two largest violet frames give
  exponents far above the others', as Io's ground in violet differs most from its map.
- Each colour set's frames are mapped onto latitude and longitude, `STEP` degrees a cell, with their
  limb darkening taken out, and the violet, blue and orange maps are divided by the green one. The
  frames of a set were taken within minutes at the same phase angle, so the ratios hold the colour
  alone. The sets' ratios are averaged on the logarithm, each cell weighted by how squarely it was
  seen and lit and by the frame's resolution, raised to `POWER`, so that the best view of each place
  outweighs the others. Triton's sets hold two to four filters; a frame whose pointing couldn't be
  fitted is left out of its set, and a set without its green frame is left out.
- The map's values rise from the moon's `zero` in proportion to the ground's brightness, so the map
  less that value holds the ground's real contrast. The USGS's maps of Io, Europa and Ganymede say
  so in their GeoTIFF tags, and with the tags' scale, Io's and Ganymede's means come to their
  geometric albedos. Triton's map was stretched for display, so its zero is fitted to the green
  frames at least `ZERO_DISC` pixels across (`fitted_zero`).
- On these moons, darker ground is redder, so on the cells the frames saw, each ratio's logarithm is
  fitted to that of the map's brightness. What the fit leaves is smoothed over `RESIDUAL_PIXELS` of
  the green frames' pixels, at their median resolution, from about 2.5 degrees for Io to 9 for
  Callisto, whose frames are the smallest, and filled in where the frames saw nothing with the mean
  of its latitude. At each texel, the ratio is the fit at the texel's own brightness, held within
  the brightness of the cells it was fitted on, times that smooth remainder. So a small bright
  crater gets the bluer colour of bright ground, and Io's coloured plains keep the colour the frames
  measured.
- Each texel's spectrum runs through the four filters' wavelengths, straight between them and flat
  beyond them, and is taken through the CIE 1931 observer to sRGB (`truecolour.py`). Where the map
  holds nothing, the texel takes the mean of its latitude. Triton's north, which no picture saw,
  takes its brightness and the remainder of its colour from the opposite latitude, 180 degrees round
  (`moons.mirrored`).
- `brightness` is the texture's mean luminance in linear light, for the game. `key light blue` is
  the blue of the only light that reaches a planet in StarLancer, (1, 1, 0.8): the texture's blue is
  divided by it. If that takes the brightest texels past 1, the whole map is scaled down until all
  but `CLIPPED` of them fit.
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import globe  # noqa: E402
import moons  # noqa: E402
import truecolour as tc  # noqa: E402
import voyager  # noqa: E402

data, listing, fits_path, moon, out = sys.argv[1:6]
size, brightness, key_blue = int(sys.argv[6]), float(sys.argv[7]), float(sys.argv[8])

# The colour maps' cells, degrees: finer for Io, whose frames are the sharpest and whose colours
# vary the most.
STEP = {'Io': 0.25, 'Europa': 0.5, 'Ganymede': 0.5, 'Callisto': 0.5, 'Triton': 0.5}[moon]
# The least cosines of the light and the view where a frame's cell counts, and the power its weight
# is raised to.
LEAST = 0.3
POWER = 3.0
# The blur of what the colour's fit to the brightness leaves, in the green frames' pixels.
RESIDUAL_PIXELS = 6
# The least brightness a texel takes, over the mean, where the map would take it lower.
FLOOR = 0.01
# The share of texels allowed past 1, and so clipped, if the map has to be scaled down to fit.
CLIPPED = 0.001
# For a map whose zero isn't known: the least disk of the green frames it's fitted to, pixels, and
# the least cosines of the light and the view where their cells count.
ZERO_DISC = 90
ZERO_LEAST = 0.5

with open(listing) as f:
    frames = [frame for frame in json.load(f)['frames'] if frame['moon'] == moon]
with open(fits_path) as f:
    fits = json.load(f)
body = moons.body(moon)
lats = np.arange(-90 + STEP / 2, 90, STEP)
lons = np.arange(STEP / 2, 360, STEP)
area = np.cos(np.radians(lats))[:, None]


def frame_view(frame):
    """A frame's image as I/F, cleaned (`moons.frame`) and its sky taken off, and its view."""
    fit = fits[frame['name']]
    img, pixel = moons.frame(data, frame)
    view = voyager.View(body, pixel, frame, fit['cx'], fit['cy'], fit['twist'], fit['scale'])
    return img - moons.sky(img, view), view


# Each filter's Minnaert exponent, the median of its frames'.
exponents = {}
for name in moons.FILTERS:
    exponents[name] = float(np.median([fits[f['name']]['k'] for f in frames
                                       if f['filter'] == name and f['name'] in fits and np.isfinite(fits[f['name']]['k'])]))
print(f"{moon}: Minnaert's exponent " + ", ".join(f"{exponents[n]:.3f} at {w:.0f} nm" for n, w in moons.FILTERS.items()))

# The moon's map, reduced to the colour maps' cells, with 0 degrees east at the left edge, south first.
full = moons.read_map(data, moon)
reduced = moons.east_at_left(moons.reduce(full, STEP), moon)[::-1]

# Each set's colour ratios, each with the set's weights, and its green frame's resolution, degrees a
# pixel.
ratios = {name: [] for name in moons.FILTERS if name != 'Green'}
weights, resolutions = [], []
sets = sorted({f['set'] for f in frames})
for set_id in sets:
    members = {f['filter']: f for f in frames if f['set'] == set_id and f['name'] in fits}
    if 'Green' not in members:
        print(f"  the set {set_id} is left out, its green frame not fitted", flush=True)
        continue
    grids = {}
    for name, frame in members.items():
        img, view = frame_view(frame)
        grids[name], mu, mu0 = voyager.albedo_grid(img, view, exponents[name], lats, lons, least=LEAST)
        if name == 'Green':
            resolution = frame['distance_km'] * view.pixel / view.scale
            resolutions.append(np.rad2deg(resolution / body.a))
            seen = np.isfinite(grids[name])
            weights.append(np.where(seen, ((np.clip(mu, 0, 1) * np.clip(mu0, 0, 1)) ** 2 / resolution ** 2) ** POWER, 0.0))
    for name in ratios:
        if name in grids:
            ratios[name].append((np.log(grids[name] / grids['Green']), weights[-1]))

# The sets' ratios, averaged with their weights.
weight = np.sum(weights, axis=0)
mean_ratio = {}
for name, maps in ratios.items():
    total = np.zeros_like(weight)
    used = np.zeros_like(weight)
    for log_ratio, w in maps:
        ok = np.isfinite(log_ratio) & (w > 0)
        total += np.where(ok, log_ratio * w, 0.0)
        used += np.where(ok, w, 0.0)
    mean_ratio[name] = np.where(used > 0, total / np.maximum(used, 1e-300), np.nan)
covered = np.all([np.isfinite(r) for r in mean_ratio.values()], axis=0)
print(f"the colour maps cover {np.sum(covered * area) / np.sum(np.ones_like(weight) * area) * 100:.1f}% of the moon")


def fitted_zero():
    """The value the map rises from, fitted to each green frame at least `ZERO_DISC` pixels across:
    the frame's albedo, where the light and the view are at least `ZERO_LEAST`, against the map
    blurred to the frame's pixel, by the reduced major axis. The median of the frames'."""
    zeros = []
    for frame in frames:
        if frame['filter'] != 'Green' or frame['name'] not in fits or frame['disc_pixels'] < ZERO_DISC:
            continue
        img, view = frame_view(frame)
        grid, _, _ = voyager.albedo_grid(img, view, fits[frame['name']]['k'], lats, lons, least=ZERO_LEAST)
        pixel = np.rad2deg(frame['distance_km'] * view.pixel / view.scale / body.a)
        blurred = voyager.smooth(reduced, pixel, STEP)
        ok = np.isfinite(grid) & np.isfinite(blurred) & np.isfinite(reduced)
        slope = np.std(grid[ok]) / np.std(blurred[ok])
        zeros.append(np.mean(blurred[ok]) - np.mean(grid[ok]) / slope)
    return float(np.median(zeros))


zero = moons.MOONS[moon]['zero']
if zero is None:
    zero = fitted_zero()
    print(f"the map's zero, fitted to the green frames: {zero:.1f}")
mirror = moons.MOONS[moon].get('mirror', False)

# Each ratio fitted to the map's brightness, and the smooth remainder.
blur = RESIDUAL_PIXELS * float(np.median(resolutions))
print(f"the remainder is smoothed over {blur:.1f} degrees")
relative = reduced - zero
relative /= np.nansum(relative * area) / np.sum(np.isfinite(relative) * area)
fit_cells = covered & np.isfinite(relative) & (relative > 0)
colour_fit, remainder = {}, {}
# The span of brightness the fits saw, which the texels' colour is held within.
seen_span = np.log(np.percentile(relative[fit_cells], [1, 99]))
for name, log_ratio in mean_ratio.items():
    cells = fit_cells & np.isfinite(log_ratio)
    slope, intercept = np.polyfit(np.log(relative[cells]), log_ratio[cells], 1)
    colour_fit[name] = (slope, intercept)
    left = np.where(cells, log_ratio - (intercept + slope * np.log(np.where(cells, relative, 1))), np.nan)
    smooth = voyager.smooth(left, blur, STEP)
    if mirror:
        smooth = moons.mirrored(smooth, STEP)
    row_means = np.nanmean(smooth, axis=1)
    row_means = np.where(np.isfinite(row_means), row_means, 0.0)
    remainder[name] = np.where(np.isfinite(smooth), smooth, row_means[:, None])
    print(f"{name}/Green: {np.exp(intercept):.3f} at the mean brightness, times the brightness to the {slope:+.3f}; "
          f"the remainder spans {np.nanpercentile(left, 5):+.3f} to {np.nanpercentile(left, 95):+.3f}")

# The texture's grid, north first, 0 degrees east at the left edge for now: the map's brightness
# over its mean, where the map holds nothing Triton's guess, or the mean of its latitude.
w, h = size, size // 2
tex_lats = 90 - (np.arange(h) + 0.5) * 180 / h
tex_lons = (np.arange(w) + 0.5) * 360 / w
tex_area = np.cos(np.radians(tex_lats))[:, None]
fine = moons.east_at_left(moons.reduce(full, 360 / w), moon) - zero
del full
fine /= np.nansum(fine * tex_area) / np.sum(np.isfinite(fine) * tex_area)
if mirror:
    fine = moons.mirrored(fine, 360 / w)
row_means = np.nanmean(fine, axis=1)
fine = np.where(np.isfinite(fine), fine, np.where(np.isfinite(row_means), row_means, np.nanmean(row_means))[:, None])
fine = np.maximum(fine, FLOOR)

# The colour maps sampled at the texels: their rows south first, wrapping round in longitude.
y = (tex_lats - lats[0]) / STEP
x = (tex_lons - lons[0]) / STEP


def at_texels(grid, rows):
    wrapped = np.concatenate([grid, grid[:, :1]], axis=1)
    yy, xx = np.meshgrid(y[rows], np.where(x < 0, x + grid.shape[1], x), indexing='ij')
    return ndimage.map_coordinates(wrapped, [yy, xx], order=1, mode='nearest')


# The spectrum through the filters, straight between them and flat beyond, as weights for linear
# sRGB: each filter's share of the light at each wavelength, summed through the observer.
lam = np.arange(380.0, 781.0, 1.0)
M = tc.matrix(lam)
wavelengths = list(moons.FILTERS.values())
K = {name: (hat[:, None] * M).sum(axis=0) for name, hat in zip(moons.FILTERS, tc.hats(lam, wavelengths))}

texture = np.empty((h, w, 3), np.float32)
for start in range(0, h, 256):
    rows = slice(start, start + 256)
    a = fine[rows].astype(np.float64)
    held = np.clip(np.log(a), *seen_span)
    rgb = a[..., None] * K['Green']
    for name, (slope, intercept) in colour_fit.items():
        ratio = np.exp(intercept + slope * held + at_texels(remainder[name], rows))
        rgb += (a * ratio)[..., None] * K[name]
    texture[rows] = rgb

# The moon's mean spectrum, for the limb's exponents at each channel's wavelength, and its colour.
mean = {'Green': 1.0}
for name, (slope, intercept) in colour_fit.items():
    mean[name] = float(np.exp(intercept))
spectrum = np.interp(lam, wavelengths, [mean[n] for n in moons.FILTERS])
channels = tc.channels(lam, spectrum, M)
order = sorted(moons.FILTERS, key=moons.FILTERS.get)
limb = np.interp(channels, [moons.FILTERS[n] for n in order], [exponents[n] for n in order])
print(f"the channels' wavelengths for {moon}'s spectrum: {np.round(channels).astype(int)} nm; their exponents, for planets.luau: "
      f"{np.round(limb, 3)}")
# The true normal albedo, for reference, from NASA's geometric albedo with Minnaert's law in green,
# by which the normal albedo is (2k + 1) / 2 times the geometric; and the mean colour at it.
normal_over_geometric = (2 * exponents['Green'] + 1) / 2
true_luminance = normal_over_geometric * moons.MOONS[moon]['albedo']
colour = (spectrum[:, None] * M).sum(axis=0)
colour *= true_luminance / tc.luminance(colour)
print(f"true mean luminance at the normal albedo, {normal_over_geometric:.3f} times the geometric albedo of "
      f"{moons.MOONS[moon]['albedo']}: {true_luminance:.3f}; in the texture: {brightness:.3f}; the mean colour at it, "
      f"8-bit sRGB {np.round(tc.encode(colour) * 255).astype(int)}")

# At the brightness asked for.
texture *= brightness / globe.area_mean(tc.luminance(texture), np.ones(h, dtype=bool), tex_lats)
texture[..., 2] /= key_blue
scale = max(1.0, np.quantile(texture[::4, ::4], 1 - CLIPPED))
texture /= scale
print(f"scaled down by {scale:.3f} to fit")

# 0 degrees east to the middle column.
texture = np.roll(texture, w // 2, axis=1)
pixels = (np.clip(texture, 0, 1) * 65535 + 0.5).astype('<u2')
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '16', '-endian', 'LSB', 'rgb:-', '-set', 'colorspace', 'RGB',
                '-colorspace', 'sRGB', '-depth', '8', '-define', 'png:exclude-chunks=date,time', out],
               input=pixels.tobytes(), check=True)
print('wrote', out)
