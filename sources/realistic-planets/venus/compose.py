"""Composes Venus's texture as a 4096x2048 sRGB PNG: north at the top and east to the right, as
`sphere.py`'s spheres map it. Its markings come from Akatsuki's ultraviolet maps of the cloud tops,
made faintly visible, and its colour from Venus's albedos in the visible.

    python3 compose.py data out.png <exaggeration> <brightness>

The cloud tops in ultraviolet:

- Akatsuki's UVI camera mapped Venus at 365 nm every two hours. Its Level 3 maps hold the radiance at
  0.125 degrees a pixel, in east longitude, with the angles of the light and the view at each cell.
  Thirteen maps from 25 to 29 June 2022, about 8 hours apart, span about one turn of the cloud tops.
  Akatsuki saw Venus at phase angles from 17 to 44 degrees then. At smaller phase angles, as earlier
  that month, the cloud droplets throw back a glory, a bright spot with rings that moves with the
  camera.
- Each map's limb darkening is taken out with Minnaert's law, I/F = B mu0^k mu^(k - 1), where the
  sun is more than `LEAST_HEIGHT` degrees up and the view more than that above the limb. Its exponent
  k is fitted to each map with each latitude's own brightness (`minnaert.py`), so that the
  bands' brightness, darker near the equator where the sun stands highest, doesn't count as limb
  darkening, and the maps' mean, about 0.86, is taken out of all of them alike. Each map is split
  into its mean over a few degrees and its detail. Over the last `INSIDE` degrees before the edge of
  what a map sees, where the limb darkening is least well taken out, its detail and its weight fade
  out, so that its edge doesn't show.
- The winds: in each band of latitude up to `WIND_LATITUDE`, the clouds' detail is compared between
  every two maps less than `WIND_HOURS` apart, the later one moved back by each turning rate tried.
  The rate that matches them best over all the pairs is the band's: about 3 degrees an hour westward
  near the equator, about 90 m/s. Farther from the equator, the views are too slanted and too few
  for the clouds to be followed, and the rate is held at its last value.
- The maps are moved back by the winds to the middle moment and averaged in two parts, each place
  weighted by a power of mu0 mu, so that the best lit and best seen views of it count most. The
  clouds change over the four days, so where two views meet, they differ. The maps' means over a few
  degrees are weighted by (mu0 mu)^`BROAD_POWER`, which blends the views over wide margins, so that no
  seam shows in the brightness. Their detail is weighted by (mu0 mu)^`DETAIL_POWER`, which keeps most
  places to the one view that sees them best, so that the detail stays sharp.
- A few maps hold ghosts of the camera: bright patches a few degrees across that the maps before and
  after don't show. Where one view is much brighter than the others, it's left out.
- Where the clouds weren't seen, the mean of what was seen within a few degrees fills in, and farther
  away, the latitude's mean, with that of the last latitudes seen most of the way round over the
  poles. Past `POLAR` degrees, where the views are slanted and few, the map fades into the latitude's
  mean.

The colour:

- Venus's geometric albedos in the Sloan bands and the Johnson B and V bands, from Mallama, Krobusek
  and Pavlov (2017), give its colour through the CIE 1931 observer (`truecolour.py`). The albedos
  are for full phase, which can't be seen, and the paper's phase curves make Venus yellower at the
  phase angles where it is seen: at 45 degrees, its B-V is about 0.81, close to the 0.82 usually
  quoted, against 0.70 at full phase. The texture takes the colour Venus has at 45 degrees
  (`photometry.py`).
- The ultraviolet markings come from an absorber whose effect fades toward red: at each wavelength,
  the spectrum's shortfall below its highest albedo, on the logarithm, over its shortfall at 365 nm.
  That is about half at 400 nm, a fifth at 436, and a twentieth at 549. At each place, the
  spectrum is darkened by the 365 nm map's ratio to its mean, raised to that share at each
  wavelength, so the dark markings are a little yellower as well as darker.
- `exaggeration` multiplies those shares: at 1, the markings are as faint as the eye would see them,
  a few per cent in the blue.
- `brightness` is the texture's mean luminance in linear light, for the game: at its true albedo
  Venus would be near white in the game's lighting, as Jupiter is.
- The texture holds the body's own colour, as the mod lights the planets with white light
  (`records.planet_light` in `records.luau`). If its brightest texels pass 1, the whole map is scaled
  down until all but `CLIPPED` of them fit.
"""
import glob
import os
import subprocess
import sys

import h5py
import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import minnaert  # noqa: E402
import photometry  # noqa: E402
import truecolour as tc  # noqa: E402

data, out = sys.argv[1], sys.argv[2]
exaggeration, brightness = float(sys.argv[3]), float(sys.argv[4])

# Akatsuki's maps' degrees a pixel, and the band the camera's filter centres on, nm.
STEP = 0.125
UV = 365.0
# The least height of the sun, and of the view above the limb, where a map is used, degrees.
LEAST_HEIGHT = 15.0
# The powers of mu0 mu that weight each view of a place, in its mean over `DETAIL` degrees and in its
# detail.
BROAD_POWER = 2
DETAIL_POWER = 8
# The winds: the latitudes they're measured up to, the degrees of latitude each band reaches either
# way, the hours two maps may be apart to be compared, and the turning rates tried, degrees an hour
# eastward. The clouds' detail is the brightness less its mean over `DETAIL` degrees. Each map's detail
# and weight fade out over the last `INSIDE` degrees before the edge of what it sees, and the winds
# follow the detail only inside them, so that the edge, which stays put, doesn't count. Two maps must
# share `WIND_SHARED` degrees of longitude along a band, on average over its rows, for a rate to be
# tried on them. The profile is smoothed over `WIND_SMOOTH` degrees of latitude.
WIND_LATITUDE = 35.0
WIND_BAND = 2.5
WIND_HOURS = 26.0
WIND_RATES = np.arange(0.0, -6.0, -0.05)
DETAIL = 3.0
INSIDE = 4.0
WIND_SHARED = 10.0
WIND_SMOOTH = 10.0
# Where the views fall short: the mu0 mu of a place's best view below which the mean nearby starts to
# fill in, and the degrees that mean is taken over. The latitude's mean is taken where at least
# `ROW_SEEN` of it was seen, and smoothed over `ROW_SMOOTH` degrees of latitude.
SEEN = 0.3
NEARBY = 5.0
ROW_SEEN = 0.25
ROW_SMOOTH = 10.0
# How much brighter than the other views a view's detail may be, on the logarithm, before it's taken
# for a ghost and fades out, and how much more before it's left out, the mu0 mu of a view that counts
# toward judging it, and the degrees round a ghost that the view is left out too.
GHOST = 0.12
GHOST_FADE = 0.03
GHOST_SEEN = 0.25
GHOST_MARGIN = 4.0
# The latitude past which the map fades into the latitude's mean, and the degrees it fades over.
POLAR = 60.0
POLAR_FADE = 10.0
# The share of texels allowed past 1, and so clipped, if the map has to be scaled down to fit.
CLIPPED = 0.001
SIZE = (4096, 2048)


def smoothstep(t):
    """0 below 0 and 1 above 1, easing between."""
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def read(path):
    """A map's radiance, the cosines of its cells' incidence and emission angles and their phase angles,
    degrees, rows from the north, NaN where it holds nothing, and its time in hours."""
    with h5py.File(path, 'r') as f:
        radiance = f['radiance'][0].astype(np.float64)
        radiance = np.where(radiance > -1e30, radiance, np.nan)

        def angle(name):
            values = f[name]
            raw = values[0].astype(np.float64)
            degrees = raw * float(values.attrs['scale_factor'][0]) + float(values.attrs['add_offset'][0])
            return np.where(raw == -32768, np.nan, degrees)[::-1]
        return (radiance[::-1], np.cos(np.radians(angle('inangle'))), np.cos(np.radians(angle('emangle'))), angle('phangle'),
                float(f['time'][0]))


def load(path):
    """A map read as `read` does, and where it's used: where the sun is more than `LEAST_HEIGHT` degrees
    up and the view more than that above the limb. The radiance and the cosines are 1 elsewhere."""
    radiance, mu0, mu, phase, hours = read(path)
    least = np.sin(np.radians(LEAST_HEIGHT))
    good = np.isfinite(radiance) & (radiance > 0) & (mu0 > least) & (mu > least)
    return np.where(good, radiance, 1), np.where(good, mu0, 1), np.where(good, mu, 1), phase, hours, good


def split(m, seen):
    """`m`'s mean over the cells seen within `DETAIL` degrees, and its detail, `m` less that mean, 0
    where it isn't seen."""
    sigma = DETAIL / STEP
    near = ndimage.gaussian_filter(seen.astype(float), sigma, mode=('nearest', 'wrap'))
    mean = ndimage.gaussian_filter(np.where(seen, m, 0), sigma, mode=('nearest', 'wrap')) / np.maximum(near, 1e-6)
    return mean, np.where(seen, m - mean, 0)


def inside(seen):
    """How far each cell is inside where it's seen, as a fade from 0 at the edge to 1 `INSIDE` degrees
    in, the longitudes wrapping round."""
    pad = 2 * int(INSIDE / STEP)
    wrapped = np.concatenate([seen[:, -pad:], seen, seen[:, :pad]], axis=1)
    return smoothstep(ndimage.distance_transform_edt(wrapped)[:, pad:-pad] * STEP / INSIDE)


def correlation(f, g):
    """The sum over all rows of f(x) g(x + s), for every shift s in columns at once, done with Fourier
    transforms."""
    return np.fft.irfft(np.sum(np.conj(np.fft.rfft(f, axis=1)) * np.fft.rfft(g, axis=1), axis=0), n=f.shape[1])


def moved(m, columns):
    """`m` with each row moved by its number of `columns` to the right, wrapping round."""
    width = m.shape[1]
    x = np.arange(width)
    return np.stack([np.interp((x - s) % width, np.arange(width + 1), np.append(row, row[0])) for row, s in zip(m, columns)])


# Each map's Minnaert exponent, and their mean, with which the limb darkening is taken out of all of
# them alike.
paths = sorted(glob.glob(f"{data}/uvi_*_365_l3b_v21.nc"))
exponents = []
for path in paths:
    radiance, mu0, mu, phase, _, good = load(path)
    exponents.append(minnaert.fit(radiance, mu0, mu, good, np.indices(good.shape)[0])[0])
    print(f"{os.path.basename(path)}: phase angle {np.median(phase[good]):.0f} degrees, Minnaert's exponent {exponents[-1]:.3f}, "
          f"the sun and the view high enough over {good.mean():.1%} of the map")
k = np.mean(exponents)
print(f"Minnaert's exponent at 365 nm, the maps' mean: {k:.3f}")

# Each map: its limb darkening taken out, as the logarithm of the brightness over its median, split
# into its mean and its detail; where its detail is followed for the winds; and each place's mu0 mu,
# fading out toward the edge, and 0 where the map isn't used.
means, details, followed, views, times = [], [], [], [], []
for path in paths:
    radiance, mu0, mu, _, hours, good = load(path)
    logs = np.log(radiance / (mu0 ** k * mu ** (k - 1)))
    mean, detail = split(np.where(good, logs - np.median(logs[good]), 0), good)
    edge = inside(good)
    means.append(mean)
    details.append(detail * edge)
    followed.append((edge == 1).astype(float))
    views.append(np.where(good, mu0 * mu, 0.0) * edge)
    times.append(hours)
height, width = means[0].shape
lats = 90 - (np.arange(height) + 0.5) * STEP

# The winds: each band's turning rate, the one that best matches every two maps close enough in time.
pairs = [(i, j) for i in range(len(times)) for j in range(i + 1, len(times)) if times[j] - times[i] <= WIND_HOURS]
centres = np.arange(-WIND_LATITUDE, WIND_LATITUDE + WIND_BAND, 2 * WIND_BAND)
rates = []
for c in centres:
    rows = (lats >= c - WIND_BAND) & (lats < c + WIND_BAND)
    together, norm = np.zeros(len(WIND_RATES)), np.zeros(len(WIND_RATES))
    for i, j in pairs:
        (a, a_seen), (b, b_seen) = [(details[n][rows], followed[n][rows]) for n in (i, j)]
        shifts = np.round(WIND_RATES * (times[j] - times[i]) / STEP).astype(int) % width
        shared = correlation(a_seen, b_seen)[shifts] / rows.sum() >= WIND_SHARED / STEP
        together += np.where(shared, correlation(a, b)[shifts], 0)
        norm += np.where(shared, np.sqrt(np.clip(correlation(a ** 2, b_seen)[shifts] * correlation(a_seen, b ** 2)[shifts], 0, None)), 0)
    rates.append(WIND_RATES[np.argmax(np.where(norm > 0, together / np.maximum(norm, 1e-12), -1))])
profile = ndimage.uniform_filter1d(np.interp(lats, centres, rates), int(WIND_SMOOTH / STEP), mode='nearest')
print("the clouds' turning rate, degrees an hour eastward: " + ", ".join(f"{r:+.2f} at {c:+.0f}" for c, r in zip(centres, rates)))
equator = profile[np.argmin(np.abs(lats))]
print(f"at the equator, {equator:.2f} degrees an hour, {equator * np.pi / 180 * 6122e3 / 3600:.0f} m/s at the cloud tops")

# The maps moved back by the winds to the middle moment.
middle = np.median(times)
moves = [-profile * (hours - middle) / STEP for hours in times]
means = [moved(m, columns).astype(np.float32) for m, columns in zip(means, moves)]
details = [moved(d, columns).astype(np.float32) for d, columns in zip(details, moves)]
views = [moved(v, columns).astype(np.float32) for v, columns in zip(views, moves)]
best = np.max(views, axis=0)

# The camera's ghosts: where a view's detail is brighter than the other views' mean there by more
# than `GHOST`, the view fades out, until it's left out where it's brighter by `GHOST_FADE` more, and
# `GHOST_MARGIN` degrees round that, which takes in what the ghost puts into the view's mean. Past
# that the view fades back in. A view is judged only where at least two others see the place well, so
# that the odd one out is known. Clouds that changed between the views differ by less, and as often
# darker as brighter.
agreed = sum(d * v ** BROAD_POWER for d, v in zip(details, views))
agreed_weight = sum(v ** BROAD_POWER for v in views)
good_views = sum(v >= GHOST_SEEN for v in views)
keeps = []
for d, v in zip(details, views):
    others = agreed_weight - v ** BROAD_POWER
    judged = (v > 0) & (good_views - (v >= GHOST_SEEN) >= 2)
    brighter = d - (agreed - d * v ** BROAD_POWER) / np.where(judged, others, 1)
    ghost = np.where(judged, smoothstep((brighter - GHOST) / GHOST_FADE), 0)
    ghost = ndimage.maximum_filter(ghost, size=2 * int(GHOST_MARGIN / STEP) + 1, mode=('nearest', 'wrap'))
    keeps.append(1 - np.minimum(1, 2 * ndimage.gaussian_filter(ghost, GHOST_MARGIN / 2 / STEP, mode=('nearest', 'wrap'))))
print(f"the views left out for ghosts: {np.mean([1 - keep[v > 0].mean() for keep, v in zip(keeps, views)]):.2%} of what each sees")

# The views averaged, their means and their detail apart.
broad, broad_weight, fine, fine_weight = (np.zeros((height, width)) for _ in range(4))
for mean, detail, view, keep in zip(means, details, views, keeps):
    view = view.astype(np.float64)
    broad += mean * keep * view ** BROAD_POWER
    broad_weight += keep * view ** BROAD_POWER
    fine += detail * keep * view ** DETAIL_POWER
    fine_weight += keep * view ** DETAIL_POWER
composite = (np.where(broad_weight > 0, broad / np.where(broad_weight > 0, broad_weight, 1), 0)
             + np.where(fine_weight > 0, fine / np.where(fine_weight > 0, fine_weight, 1), 0))

# Where the clouds weren't seen well, the mean of what was seen nearby, and farther away, the latitude's
# mean, held at that of the last latitudes seen most of the way round over the poles. Past `POLAR`
# degrees, the latitude's mean.
share = smoothstep(best / SEEN)
near = ndimage.gaussian_filter(share, NEARBY / STEP, mode=('nearest', 'wrap'))
nearby = ndimage.gaussian_filter(composite * share, NEARBY / STEP, mode=('nearest', 'wrap')) / np.maximum(near, 1e-12)
seen_rows = share.mean(axis=1) >= ROW_SEEN
row_mean = np.sum(composite * share, axis=1) / np.maximum(share.sum(axis=1), 1e-12)
row_mean = np.interp(lats, lats[seen_rows][::-1], row_mean[seen_rows][::-1])
row_mean = ndimage.uniform_filter1d(row_mean, int(ROW_SMOOTH / STEP), mode='nearest')
reach = smoothstep(2 * near)
fill = nearby * reach + row_mean[:, None] * (1 - reach)
logs = composite * share + fill * (1 - share)
polar = smoothstep((np.abs(lats) - POLAR) / POLAR_FADE)[:, None]
logs = logs * (1 - polar) + row_mean[:, None] * polar
area = np.cos(np.radians(lats))[:, None]
logs -= np.sum(logs * area) / (area.sum() * width)
print(f"the clouds seen most of the way round from {lats[seen_rows].min():.0f} to {lats[seen_rows].max():.0f} degrees; the 365 nm map's ratio to its mean "
      f"from {np.exp(np.percentile(logs, 1)):.2f} to {np.exp(np.percentile(logs, 99)):.2f} between the 1st and 99th percentiles")

# The spectrum at `photometry.PHASE` degrees, and each wavelength's share of the absorber's effect at
# 365 nm.
points, values = photometry.spectrum()
print(f"B-V at full phase: {photometry.b_minus_v([b[1] for b in photometry.BANDS.values()]):.2f}, "
      f"at {photometry.PHASE:.0f} degrees: {photometry.b_minus_v(values):.2f}")
lam = np.arange(380.0, 781.0, 1.0)
albedo = np.interp(lam, points, values)
peak = np.argmax(values)
at_uv = np.interp(UV, points, values)
shares = np.where(lam < points[peak], np.log(albedo / values[peak]) / np.log(at_uv / values[peak]), 0)
print("the absorber's share of its 365 nm effect: " + ", ".join(f"{np.interp(w, lam, shares):.2f} at {w:.0f} nm" for w in (400, 436, 469, 549, 616)))
M = tc.matrix(lam)
geometric = (albedo[:, None] * M).sum(axis=0)

# Each place's colour from a table over the logarithm of the 365 nm ratio.
grid = np.linspace(logs.min(), logs.max(), 1024)
table = (albedo[None, :] * np.exp(exaggeration * shares[None, :] * grid[:, None])) @ M
texture = np.stack([np.interp(logs, grid, table[:, c]) for c in range(3)], axis=-1)

# At the brightness asked for.
scale = brightness / (np.sum(tc.luminance(texture) * area) / (area.sum() * width))
texture *= scale
print(f"geometric albedo, linear sRGB {np.round(geometric, 4)}, as 8-bit sRGB {np.round(tc.encode(geometric) * 255).astype(int)}, "
      f"luminance {tc.luminance(geometric):.3f}; the texture's mean luminance: {brightness:.3f}")
fit = max(1.0, np.quantile(texture, 1 - CLIPPED))
texture /= fit
print(f"scaled down by {fit:.3f} to fit")

# Resampled to the texture's grid, each texel's middle at its latitude and longitude, 0 degrees in the
# middle column, in linear light. The maps' cells are centred half a step from whole degrees.
w, h = SIZE
pad = 4
padded = np.concatenate([texture[:, -pad:], texture, texture[:, :pad]], axis=1)
row = (np.arange(h) + 0.5) * 180 / h / STEP - 0.5
column = ((np.arange(w) + 0.5) * 360 / w - 180) % 360 / STEP - 0.5 + pad
rr, cc = np.meshgrid(row, column, indexing='ij')
img = np.stack([ndimage.map_coordinates(padded[..., c], [rr, cc], order=3, mode='nearest') for c in range(3)], axis=-1)
pixels = (np.clip(img, 0, 1) * 65535 + 0.5).astype('<u2')
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '16', '-endian', 'LSB', 'rgb:-', '-set', 'colorspace', 'RGB',
                '-colorspace', 'sRGB', '-depth', '8', '-define', 'png:exclude-chunks=date,time', out],
               input=pixels.tobytes(), check=True)
print('wrote', out)
