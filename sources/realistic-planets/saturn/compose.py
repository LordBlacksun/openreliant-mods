"""Composes Saturn's texture as a 4096x2048 sRGB PNG: north at the top and east to the right, as
`sphere.py`'s spheres map it. The detail comes from Cassini's global maps of 11 August 2011, the
bands' brightness from Hubble's calibrated OPAL maps of August 2025, and the north polar cap from
Hubble's maps of June 2018.

    python3 compose.py data data/1993.tab out.png <stretch> <brightness> <key light blue>

Hubble's maps:

- OPAL's maps are calibrated: I/F, with the limb darkening taken out by Minnaert's law, at 0.2
  degrees a pixel in planetographic latitude. Their files hold the north first and put 360 degrees
  west at the left edge, west decreasing to the right, so east increases to the right, as seen from
  outside: between Hubble's two rotations, 9.4 hours apart, the equatorial clouds move 14 degrees to
  the right, as Saturn's eastward equatorial jet carries them. The texture keeps that order, with 0
  degrees in the middle column.
- Moons and their shadows cross the maps. Spots that stand out from their latitude by more than
  `SPOT`, smaller than `SPOT_AREA` pixels, are filled from their row's median around them.
- The second rotation is moved back by the winds measured between the two, latitude by latitude, and
  the two are averaged. Near the equator, the broad patches along each latitude at the seams between
  Hubble's orbits, which differ from one rotation to the other, are taken out.
- In August 2025 Hubble saw Saturn three months after its equinox, with the rings nearly edge on, so
  both hemispheres show. The rings and their shadow cross the disk just north of the equator; where
  the brightness varies from one pixel to the next along a latitude by more than `ROUGH`, the rows
  near the equator are filled along each column, across the gap, from the rows on either side.
- Past about 77 degrees north Hubble saw the clouds edge on in 2025. The cap comes from the maps of
  June 2018, when Hubble saw the north from 26 degrees above, hexagon and all. Each filter's 2018 map
  is scaled to 2025's mean over `MATCH` and blended in over `BLEND`. The south is seen down to about
  84 degrees, and its last `FADE` degrees fade into their own mean colour, which fills the small cap.
- The F467M maps of 2025 aren't used: their Minnaert exponent, 0.86 against 0.65 at 502 nm,
  over-corrects toward the limb, so that at 70 degrees north they read brighter than the 502 nm maps,
  which Saturn's spectrum never does.

Cassini's maps, by Li, West, Jiang and Knowles, from the PDS Atmospheres Node:

- They hold 0.1 degrees a pixel in planetocentric latitude, made from frames of about 160 km a pixel
  in Cassini's red, green and blue filters. Their values are levels from 30, where they hold no data,
  to 255, and their makers took the light's angle out by a method of their own rather than by a set
  law.
- The pieces of the mosaic meet in seams where a map steps from one column to the next far more than
  usual. Each row's step there is taken out and spread over a few degrees, and where the winds moved
  the clouds between the pieces' frames, so that they don't line up across a seam, the map is
  blurred a little along the latitude there.
- Rows with streaks, where a map was drawn from too few of the frames' pixels, are found as rows
  whose fine detail repeats half a degree south, which clouds' detail doesn't, and left out. So are
  the latitudes of the rings' shadow, and, joined to it, those that the C ring's thin shadow darkens.
- Each filter's contrast is brought to Hubble's at its wavelength, measured as the spread of the
  logarithm of the brightness between its 10th and 90th percentiles within 60 degrees of the equator.
  Measured so, Cassini's published levels have 2.1 to 5.3 times Hubble's contrast: each filter's map
  was stretched for display on its own, the green the most.
- Along each latitude Cassini's maps are scaled to Hubble's mean there, smoothed over `RATIO_SMOOTH`
  degrees, so that the bands' brightness is Hubble's and the detail Cassini's. Where Cassini's maps
  hold nothing, Hubble's, interpolated to Cassini's wavelengths, fill in, blended over `FEATHER`
  degrees.

The texture:

- The colour is true colour (`truecolour.py`) of Karkoschka's albedo spectrum of Saturn, bent at
  each place through the 463, 568 and 647 nm maps' ratios to their means. `stretch` multiplies the
  contrast of the luminance alone, on its logarithm, for the game, keeping each place's colour: 1
  keeps Saturn's own.
- `brightness` is the texture's mean luminance in linear light, for the game: at its true normal
  albedo Saturn would be near white in the game's lighting, as Jupiter is.
- `key light blue` is the blue of the only light that reaches a planet in StarLancer, (1, 1, 0.8):
  the texture's blue is divided by it, so that the planet shows its own colour in the game. If that
  takes the brightest texels past 1, the whole map is scaled down until all but `CLIPPED` of them fit.
- For `haze.py`, it writes what an I/F of 1 in each of Cassini's filters becomes in the texture's
  linear sRGB, as the texture takes a place's albedo in them, to `data/colour.json`.
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import cassini  # noqa: E402
import fits  # noqa: E402
import globe  # noqa: E402
import truecolour as tc  # noqa: E402

data, spectrum, out = sys.argv[1], sys.argv[2], sys.argv[3]
stretch, brightness, key_blue = float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6])

# Saturn's radii, km (IAU), as OPAL's maps take them, for turning planetographic latitudes into
# planetocentric ones.
EQUATOR, POLE = 60268.0, 54364.0
# OPAL's maps, both rotations of August 2025 and the first of June 2018: each filter's wavelength, nm,
# and the factor that turns its values into I/F, from the maps' readmes.
OPAL = {
    '2025a': {'f395n': (395.0, 0.00231), 'f502n': (502.0, 0.00285), 'f631n': (631.0, 0.00362)},
    '2025b': {'f395n': (395.0, 0.00231), 'f502n': (502.0, 0.00285), 'f631n': (631.0, 0.00362)},
    '2018a': {'f395n': (395.0, 0.00255), 'f502n': (502.0, 0.00313), 'f631n': (631.0, 0.00335)},
}
# OPAL's degrees a pixel.
OPAL_STEP = 0.2
# The roughness past which a row isn't trusted, the latitudes round the equator searched for the
# rings' gap, degrees, and the rows added to the gap on either side.
ROUGH = 0.01
EQUATORIAL = 10.0
GAP_MARGIN = 2
# The rows beyond each side of the gap whose mean it is filled from, and the degrees of longitude
# that mean is smoothed over, so that the fill shows no streaks.
GAP_EDGE = 3
GAP_SMOOTH = 6.0
# Moons and their shadows: how far a spot stands out from its latitude, its largest area in pixels,
# and the pixels about it that are filled with it.
SPOT = 0.06
SPOT_AREA = 600
SPOT_MARGIN = 3
# The winds between the two rotations: the degrees of latitude each band they are measured over
# reaches either way, the columns searched, the least correlation a band's drift is kept at, and the
# largest drift kept, in columns (Saturn's equatorial jet moves the clouds about 74).
WIND_BAND = 2.0
WIND_REACH = 120
WIND_MATCH = 0.15
WIND_MOST = 80
# The degrees of longitude the clouds' detail is measured against the running mean over.
DETAIL_WIDTH = 12.0
# Near the equator, the degrees of latitude within which each row's broad patches along it are taken
# out, the degrees over which that fades, and the degrees of longitude a patch is broader than.
PATCHES = 12.0
PATCHES_FADE = 3.0
PATCH_WIDTH = 30.0
# The north cap from 2018: the latitudes each filter is matched over, and blended over, degrees.
MATCH = (66.0, 74.0)
BLEND = (70.0, 76.0)
# How many degrees before the end of the southern data its detail fades into the cap's colour, and how
# many degrees of data that colour is the mean of.
FADE = 3.0
CAP_MEAN = 2.0
# Cassini's maps of 11 August 2011, one for each filter (`cassini.FILTERS`): their degrees a pixel,
# and the level they hold where they have no data, their lowest.
CASSINI_STEP = 0.1
NO_DATA = 30
# How far inside the edge of Cassini's data, degrees, Hubble's maps give way to it, the degrees of
# latitude the ratio between the two along each latitude is smoothed over, and the widest band of
# latitudes with data between two without that is left to Hubble's maps too.
FEATHER = 1.5
RATIO_SMOOTH = 3.0
JOIN = 6.0
# Streaks: where a map was drawn from too few of the frames' pixels, its fine detail, the brightness
# less its mean over `STREAK_DETAIL` degrees along the latitude, repeats on the row `STREAK_APART`
# degrees south, which clouds' detail doesn't: rows that correlate past `STREAK` are left to Hubble's.
STREAK_DETAIL = 0.9
STREAK_APART = 0.5
STREAK = 0.3
# The seams between the pieces of Cassini's mosaics: the degrees of latitude of each band they are
# found in, and how many times the usual change from one column to the next a seam steps by. Each
# row's step is the median of the differences across the seam between the `SEAM_SIDE` columns nearest
# it on either side, which the clouds barely change over, smoothed over `SEAM_SMOOTH` degrees of
# latitude and no larger than `SEAM_LARGEST` on the logarithm, and it is spread over `SEAM_SPREAD`
# degrees of longitude either side.
SEAM_BAND = 15.0
SEAM_STEP = 8.0
SEAM_SIDE = 3
SEAM_SMOOTH = 1.0
SEAM_LARGEST = 0.12
SEAM_SPREAD = 5.0
# The pieces were taken hours apart, so the winds had moved the clouds and they don't line up across a
# seam. Where the clouds either side differ by more than `SEAM_MISMATCH` on the logarithm, smoothed over
# `SEAM_SMOOTH` degrees of latitude, the map gives way within about `SEAM_SOFTEN` degrees of the seam
# to itself blurred along the latitude by `SEAM_BLUR` degrees, so that the break becomes a short smear.
SEAM_MISMATCH = 0.05
SEAM_SOFTEN = 0.8
SEAM_BLUR = 0.4
# The latitudes each Cassini filter's contrast is measured over, against Hubble's, and the
# percentiles its spread is measured between.
CONTRAST_LATITUDE = 60.0
PERCENTILES = (0.1, 0.9)
# The latitudes the filters' means are taken over.
MEAN_LATITUDES = (-60.0, 60.0)
# The share of texels allowed past 1, and so clipped, if the map has to be scaled down to fit.
CLIPPED = 0.001
SIZE = (4096, 2048)


def centric(graphic):
    """Planetocentric latitudes from planetographic ones, degrees."""
    return np.degrees(np.arctan(np.tan(np.radians(graphic)) * (POLE / EQUATOR) ** 2))


def graphic(centric_lat):
    """Planetographic latitudes from planetocentric ones, degrees."""
    return np.degrees(np.arctan(np.tan(np.radians(centric_lat)) / (POLE / EQUATOR) ** 2))


def smoothstep(t):
    """0 below 0 and 1 above 1, easing between."""
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def row_medians(m):
    """Each row's median over the cells that hold data, or NaN for a row with none."""
    medians = np.full((m.shape[0], 1), np.nan)
    seen = np.isfinite(m).any(axis=1)
    medians[seen, 0] = np.nanmedian(m[seen], axis=1)
    return medians


def row_means(m):
    """Each row's mean over the cells that hold data, or NaN for a row with none."""
    seen = np.isfinite(m)
    count = seen.sum(axis=1, keepdims=True)
    total = np.where(seen, m, 0).sum(axis=1, keepdims=True)
    return np.where(count > 0, total / np.maximum(count, 1), np.nan)


def roughness(m):
    """How much the brightness varies from one pixel to the next along each row, over the row's mean."""
    steps = np.diff(m, axis=1)
    spread_ = np.sqrt(np.maximum(row_means(steps * steps) - row_means(steps) ** 2, 0))
    return (spread_ / row_means(m))[:, 0]


def spread(values, weights):
    """How far apart the logarithms of `values` lie between the percentiles, weighted by area."""
    order = np.argsort(values)
    logs, cumulative = np.log(values[order]), np.cumsum(weights[order])
    cumulative /= cumulative[-1]
    low, high = PERCENTILES
    return np.interp(high, cumulative, logs) - np.interp(low, cumulative, logs)


def load(rotation):
    """A rotation's maps as I/F, by wavelength: rows from 90 north to 90 south, NaN where they hold
    nothing."""
    maps = {}
    for name, (wavelength, factor) in OPAL[rotation].items():
        image = fits.image(f"{data}/hlsp_opal_hst_wfc3-uvis_saturn-{rotation}_{name}_v1_globalmap.fits")
        maps[wavelength] = np.where(image > 0, image * factor, np.nan)
    return maps


def clear_spots(maps):
    """Fills the moons and their shadows: spots that stand out from their row's median around them in
    any map, filled from that median. Returns how many."""
    around = {w: ndimage.median_filter(np.nan_to_num(m), size=(1, 61), mode='wrap') for w, m in maps.items()}
    stands_out = np.zeros(next(iter(maps.values())).shape, bool)
    for w, m in maps.items():
        stands_out |= np.abs(np.nan_to_num(m / np.where(around[w] > 0, around[w], np.nan) - 1)) > SPOT
    labels, count = ndimage.label(stands_out)
    sizes = ndimage.sum(stands_out, labels, range(1, count + 1))
    spots = np.isin(labels, 1 + np.nonzero(sizes < SPOT_AREA)[0])
    spots = ndimage.binary_dilation(spots, iterations=SPOT_MARGIN) & np.isfinite(next(iter(maps.values())))
    for w, m in maps.items():
        maps[w] = np.where(spots, around[w], m)
    return int(np.count_nonzero(sizes < SPOT_AREA))


def details(m):
    """A map's departures from its latitude's median, less their running mean along the latitude: the
    clouds' detail."""
    r = np.nan_to_num(m / row_medians(m) - 1)
    return r - ndimage.uniform_filter1d(r, int(round(DETAIL_WIDTH / OPAL_STEP)), axis=1, mode='wrap')


def drift(first, second, latitudes):
    """How many columns the clouds of `second` lie east of those of `first`, at each row: measured in
    bands of latitude where they match well, and interpolated between."""
    a, b = details(first), details(second)
    centres, shifts = [], []
    for centre in np.arange(-90 + WIND_BAND, 90, WIND_BAND):
        rows = (latitudes >= centre - WIND_BAND) & (latitudes < centre + WIND_BAND)
        scores = np.array([np.sum(a[rows] * np.roll(b[rows], -s, axis=1)) for s in range(-WIND_REACH, WIND_REACH + 1)])
        norm = np.sqrt(np.sum(a[rows] ** 2) * np.sum(b[rows] ** 2))
        k = int(np.argmax(scores))
        if norm == 0 or scores[k] / norm < WIND_MATCH or not 0 < k < len(scores) - 1:
            continue
        y0, y1, y2 = scores[k - 1:k + 2]
        shift = k - WIND_REACH + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
        if abs(shift) <= WIND_MOST:
            centres.append(centre)
            shifts.append(shift)
    return np.interp(latitudes, centres, shifts)


def moved(m, columns):
    """`m` with each row moved west by its number of `columns`, wrapping round."""
    width = m.shape[1]
    x = np.arange(width)
    return np.stack([np.interp((x + s) % width, np.arange(width + 1), np.append(row, row[0])) for row, s in zip(m, columns)])


def averaged(first, second):
    """Two rotations' maps as one: their mean, or the one that holds data where the other doesn't."""
    return {w: np.where(np.isnan(first[w]), second[w], np.where(np.isnan(second[w]), first[w], (first[w] + second[w]) / 2))
            for w in first}


def without_patches(m, latitudes):
    """`m` with each row near the equator divided by its brightness over `PATCH_WIDTH` degrees of
    longitude about each point, over the row's mean: the patches at the seams between Hubble's orbits
    go, and the clouds narrower than that stay."""
    width = int(round(PATCH_WIDTH / OPAL_STEP))
    weight = smoothstep((PATCHES - np.abs(latitudes)) / PATCHES_FADE)[:, None]
    filled = np.where(np.isfinite(m), m, row_means(m))
    broad = ndimage.uniform_filter1d(np.nan_to_num(filled), width, axis=1, mode='wrap')
    factor = np.where(broad > 0, broad / np.where(broad > 0, row_means(np.where(np.isfinite(m), broad, np.nan)), 1), 1)
    return m / (1 + weight * (np.nan_to_num(factor, nan=1.0) - 1))


def streaked(m):
    """The rows of a Cassini map whose fine detail repeats on the row `STREAK_APART` degrees south:
    streaks, not clouds."""
    logs = np.log(m)
    detail = logs - ndimage.uniform_filter1d(np.nan_to_num(logs), int(round(STREAK_DETAIL / CASSINI_STEP)), axis=1, mode='wrap')
    apart = int(round(STREAK_APART / CASSINI_STEP))
    rows = np.zeros(len(m), bool)
    for i in range(len(m) - apart):
        a, b = detail[i], detail[i + apart]
        both = np.isfinite(a) & np.isfinite(b)
        if both.sum() <= m.shape[1] // 4:
            continue
        a, b = a[both] - a[both].mean(), b[both] - b[both].mean()
        norm = np.sqrt(np.sum(a * a) * np.sum(b * b))
        if norm > 0 and np.sum(a * b) / norm > STREAK:
            rows[i:i + apart + 1] = True
    return rows


def seams(m, latitudes):
    """The columns where a Cassini map steps, along some band of latitude, by more than `SEAM_STEP`
    times the usual change from one column to the next: where the pieces of the mosaic meet. Of two
    closer than the columns measured on either side, the one with the larger step is kept."""
    logs = np.log(m)
    width = m.shape[1]
    found = {}
    for top in np.arange(90, -90, -SEAM_BAND):
        rows = (latitudes <= top) & (latitudes > top - SEAM_BAND) & np.isfinite(logs).all(axis=1)
        if rows.sum() < SEAM_BAND / CASSINI_STEP / 2:
            continue
        profile = logs[rows].mean(axis=0)
        steps = np.abs(profile - np.roll(profile, 1)) / np.median(np.abs(profile - np.roll(profile, 1)))
        for column in np.nonzero(steps > SEAM_STEP)[0]:
            found[int(column)] = max(found.get(int(column), 0), steps[column])
    kept = []
    for column in sorted(found, key=found.get, reverse=True):
        if all(min(abs(column - other), width - abs(column - other)) >= 2 * SEAM_SIDE for other in kept):
            kept.append(column)
    return sorted(kept)


def across(logs, column):
    """Each row's step across the seam at `column`: the median of the differences between the
    `SEAM_SIDE` columns nearest it on either side."""
    width = logs.shape[1]
    after = logs[:, (column + np.arange(SEAM_SIDE)) % width]
    before = logs[:, (column - 1 - np.arange(SEAM_SIDE)) % width]
    return np.nan_to_num(np.median(after - before, axis=1))


def without_seams(m, columns):
    """`m` with its step at each of `columns` taken out along every row, and spread instead over
    `SEAM_SPREAD` degrees either side, where it doesn't show, and the clouds that don't line up across
    each seam blurred into each other."""
    logs = np.log(m)
    width = m.shape[1]
    smooth = int(SEAM_SMOOTH / CASSINI_STEP)
    reach = int(SEAM_SPREAD / CASSINI_STEP)
    offsets = np.arange(-reach, reach)
    ramp = smoothstep((offsets + reach + 0.5) / (2 * reach)) - (offsets >= 0)
    correction = np.zeros_like(logs)
    for column in columns:
        step = np.clip(ndimage.uniform_filter1d(across(logs, column), smooth), -SEAM_LARGEST, SEAM_LARGEST)
        correction[:, (column + offsets) % width] += step[:, None] * ramp
    logs = logs + correction
    blurred = ndimage.gaussian_filter1d(np.nan_to_num(logs), SEAM_BLUR / CASSINI_STEP, axis=1, mode='wrap')
    x = np.arange(width)
    for column in columns:
        mismatch = ndimage.uniform_filter1d(np.abs(across(logs, column)), smooth)
        apart = np.minimum(np.abs(x - column), width - np.abs(x - column)) * CASSINI_STEP
        weight = np.clip(mismatch / SEAM_MISMATCH, 0, 1)[:, None] * np.exp(-(apart / SEAM_SOFTEN) ** 2)
        logs = np.where(np.isfinite(logs), logs * (1 - weight) + blurred * weight, logs)
    return np.exp(logs)


def at_wavelength(maps, wavelength):
    """Maps by wavelength, interpolated to `wavelength`, and held flat past the ends."""
    known = sorted(maps)
    wavelength = np.clip(wavelength, known[0], known[-1])
    i = min(max(int(np.searchsorted(known, wavelength)), 1), len(known) - 1)
    t = (wavelength - known[i - 1]) / (known[i] - known[i - 1])
    return maps[known[i - 1]] * (1 - t) + maps[known[i]] * t


# Hubble's maps of August 2025: both rotations, cleared of moons and their shadows, the second moved
# back by the winds to line up with the first, and the two averaged.
first, second = load('2025a'), load('2025b')
opal_lats = 90 - (np.arange(first[395.0].shape[0]) + 0.5) * OPAL_STEP
opal_centric = centric(opal_lats)
print(f"moons and shadows filled: {clear_spots(first)} spots in the first rotation, {clear_spots(second)} in the second")
winds = drift(first[631.0], second[631.0], opal_lats)
print(f"the clouds moved east by up to {winds.max() * OPAL_STEP:.1f} degrees between the rotations")
hubble = averaged(first, {w: moved(m, winds) for w, m in second.items()})
# Near the equator, the broad patches along each latitude at the seams between Hubble's orbits.
hubble = {w: without_patches(m, opal_lats) for w, m in hubble.items()}

# The rings' gap near the equator: the rows round the ones that hold nothing that aren't trusted,
# and `GAP_MARGIN` more on either side, filled along each column from the mean of the `GAP_EDGE` rows
# beyond either side, smoothed along the latitude.
rough = np.max([roughness(m) for m in hubble.values()], axis=0)
untrusted = ~(np.isfinite(rough) & (rough < ROUGH))
holes = np.nonzero((np.abs(opal_lats) < EQUATORIAL) & np.any([np.isnan(m).any(axis=1) for m in hubble.values()], axis=0))[0]
top, bottom = holes.min(), holes.max()
while untrusted[top - 1]:
    top -= 1
while untrusted[bottom + 1]:
    bottom += 1
top, bottom = top - GAP_MARGIN - 1, bottom + GAP_MARGIN + 1
print(f"the rings' gap: filled across from {opal_lats[top]:.1f} to {opal_lats[bottom]:.1f} degrees")
t = ((np.arange(top, bottom + 1) - top) / (bottom - top))[:, None]
along = int(round(GAP_SMOOTH / OPAL_STEP))
for m in hubble.values():
    north = ndimage.uniform_filter1d(m[top - GAP_EDGE + 1:top + 1].mean(axis=0), along, mode='wrap')
    south = ndimage.uniform_filter1d(m[bottom:bottom + GAP_EDGE].mean(axis=0), along, mode='wrap')
    m[top:bottom + 1] = north * (1 - t) + south * t

# The north cap from 2018, each filter scaled to 2025's mean where both are good.
cap = load('2018a')
print(f"moons and shadows filled in 2018's maps: {clear_spots(cap)} spots")
match = (opal_lats >= MATCH[0]) & (opal_lats <= MATCH[1])
blend = smoothstep((opal_lats - BLEND[0]) / (BLEND[1] - BLEND[0]))[:, None]
for w in sorted(hubble):
    gain = globe.area_mean(hubble[w], match, opal_centric) / globe.area_mean(cap[w], match, opal_centric)
    hubble[w] = np.where(blend > 0, np.where(blend < 1, hubble[w], 0) * (1 - blend) + cap[w] * gain * blend, hubble[w])
    print(f"{w:.0f} nm: 2018's cap scaled by {gain:.3f}")

# The south: the last trusted degrees fade into their own mean colour, which fills the cap.
rough = np.max([roughness(m) for m in hubble.values()], axis=0)
southern = opal_lats < -EQUATORIAL
last = opal_lats[southern][np.nonzero(~(np.isfinite(rough[southern]) & (rough[southern] < ROUGH)))[0][0]] + OPAL_STEP
faded = np.where(opal_lats < 0, smoothstep(((last + FADE) - opal_lats) / FADE), 0.0)[:, None]
ends = (opal_lats >= last) & (opal_lats <= last + CAP_MEAN)
for w, m in hubble.items():
    hubble[w] = np.where(faded > 0, np.nan_to_num(m) * (1 - faded) + np.nanmean(m[ends]) * faded, m)
print(f"the south trusted to {last:.1f} degrees, faded into its cap over {FADE:.0f}")
assert all(np.isfinite(m).all() for m in hubble.values())
# Saturn's true normal albedo at 502 nm, for reference.
true_green = globe.area_mean(hubble[502.0], (opal_lats >= MEAN_LATITUDES[0]) & (opal_lats <= MEAN_LATITUDES[1]), opal_centric)

# Cassini's maps: rows from the north pole south at planetocentric latitudes, and columns from 360
# degrees west down to 0, so east increases to the right. The first column holds no data and the last
# is 0 degrees, so the maps are turned to start there.
cassini_maps = {}
for name, wavelength in cassini.FILTERS.items():
    image = np.roll(fits.image(f"{data}/Cassini_ISS_{name}_Saturn_global_map.fits")[:, 1:].astype(np.float64), 1, axis=1)
    cassini_maps[wavelength] = np.where(np.isfinite(image) & (image > NO_DATA), image, np.nan)
lats = 90 - np.arange(cassini_maps[647.0].shape[0]) * CASSINI_STEP
seen = np.all([np.isfinite(m) for m in cassini_maps.values()], axis=0)
# Streaked rows, and a band of data narrower than `JOIN` degrees between latitudes without, such as the
# one between the rings' shadow and the line along the equator, which the C ring's thin shadow still
# darkens, are left to Hubble's maps too.
streaks = np.any([streaked(m) for m in cassini_maps.values()], axis=0)
print(f"streaks left out: {streaks.sum() * CASSINI_STEP:.1f} degrees of latitude")
blank = ~seen.any(axis=1) | streaks
seen &= ~ndimage.binary_closing(blank, structure=np.ones(int(JOIN / CASSINI_STEP) + 1, bool))[:, None]
# The seams between the mosaic's pieces, found on the red map, which all three share.
joins = seams(cassini_maps[647.0], lats)
cassini_maps = {w: without_seams(m, joins) for w, m in cassini_maps.items()}
print(f"seams taken out at {len(joins)} longitudes: {', '.join(f'{c * CASSINI_STEP:.0f}' for c in joins)} degrees east")
print(f"Cassini's maps hold {seen.mean():.1%} of the grid, from {lats[seen.any(axis=1)].min():.1f} to "
      f"{lats[seen.any(axis=1)].max():.1f} degrees")

# Hubble's maps on Cassini's grid, at its wavelengths.
opal_rows = (90 - graphic(lats)) / OPAL_STEP - 0.5
opal_columns = np.arange(seen.shape[1]) * CASSINI_STEP / OPAL_STEP - 0.5
rr, cc = np.meshgrid(opal_rows, opal_columns + 1, indexing='ij')
on_grid = {w: ndimage.map_coordinates(np.concatenate([m[:, -1:], m, m[:, :1]], axis=1), [rr, cc], order=1, mode='nearest')
           for w, m in hubble.items()}

# Cassini's maps where they hold data, giving way to Hubble's over `FEATHER` degrees at the edge, and
# Hubble's elsewhere. Each of Cassini's maps is first brought to Hubble's contrast at its wavelength,
# about its geometric mean, which also undoes any curve its levels were encoded with, then scaled
# along each latitude to Hubble's mean there, the ratio smoothed over `RATIO_SMOOTH` degrees of
# latitude, so that the bands' brightness is Hubble's, calibrated, and the detail Cassini's.
share = smoothstep(ndimage.distance_transform_edt(seen) * CASSINI_STEP / FEATHER)
full = share.min(axis=1) >= 1
compared = (share >= 1) & (np.abs(lats) <= CONTRAST_LATITUDE)[:, None]
cells = np.broadcast_to(np.cos(np.radians(lats))[:, None], seen.shape)[compared]
maps = {}
for w, m in cassini_maps.items():
    reference = at_wavelength(on_grid, w)
    exponent = spread(reference[compared], cells) / spread(m[compared], cells)
    pivot = np.exp(np.sum(np.log(m[compared]) * cells) / cells.sum())
    m = pivot * (m / pivot) ** exponent
    ratio = np.full(len(lats), np.nan)
    ratio[full] = reference[full].mean(axis=1) / np.nanmean(m[full], axis=1)
    smoothed = ndimage.uniform_filter1d(np.interp(lats[::-1], lats[full][::-1], ratio[full][::-1]), int(RATIO_SMOOTH / CASSINI_STEP))[::-1]
    maps[w] = np.where(share > 0, np.nan_to_num(m) * smoothed[:, None] * share + reference * (1 - share), reference)
    print(f"{w:.0f} nm: Cassini's contrast scaled by {exponent:.3f} to Hubble's, and its bands by "
          f"{np.nanmin(ratio) / np.nanmedian(ratio):.2f} to {np.nanmax(ratio) / np.nanmedian(ratio):.2f} of its median")
wavelengths = sorted(maps)

# Each map's ratio to its mean.
band = (lats >= MEAN_LATITUDES[0]) & (lats <= MEAN_LATITUDES[1])
everywhere = np.ones_like(lats, dtype=bool)
ratio = {}
for w, m in maps.items():
    r = m / globe.area_mean(m, band, lats)
    ratio[w] = r / globe.area_mean(r, everywhere, lats)
    print(f"{w:.0f} nm: contrast from the 10th to the 90th percentile {np.percentile(m[band], 90) / np.percentile(m[band], 10):.3f}")

# The spectrum bent through each filter by hat functions that sum to one, flat beyond them.
lam, albedo = tc.karkoschka(spectrum, 'saturn')
M = tc.matrix(lam)
hats = dict(zip(wavelengths, tc.hats(lam, wavelengths)))
assert np.allclose(sum(hats.values()), 1)
K = {w: ((albedo * h)[:, None] * M).sum(axis=0) for w, h in hats.items()}
geometric = sum(K.values())
texture = sum(ratio[w][..., None] * K[w] for w in wavelengths)
# The luminance's contrast stretched on its logarithm, each place keeping its colour.
luminance = tc.luminance(texture)
mean = globe.area_mean(luminance, everywhere, lats)
texture *= ((luminance / mean) ** (stretch - 1))[..., None]
texture *= mean / globe.area_mean(tc.luminance(texture), everywhere, lats)

# Each channel's wavelength for Saturn's spectrum, the mean of the wavelengths it takes in, for the
# limb's exponents.
channel = tc.channels(lam, albedo, M)
print(f"the channels' wavelengths for Saturn's spectrum: {np.round(channel).astype(int)} nm")

# At the brightness asked for; the true normal albedo, measured on Hubble's 502 nm maps, for reference.
normal_over_geometric = true_green / np.interp(502.0, lam, albedo)
scale = brightness / globe.area_mean(tc.luminance(texture), everywhere, lats)
texture *= scale
print(f"geometric albedo, linear sRGB {np.round(geometric, 4)}, as 8-bit sRGB {np.round(tc.encode(geometric) * 255).astype(int)}; "
      f"true mean luminance at the normal albedo, {normal_over_geometric:.3f} times the geometric: "
      f"{normal_over_geometric * tc.luminance(geometric):.3f}; in the texture: {brightness:.3f}")
print(f"the equatorial zone's mean luminance in the texture, within 15 degrees: "
      f"{globe.area_mean(tc.luminance(texture), np.abs(lats) <= 15, lats):.3f}")
texture[..., 2] /= key_blue
fit = max(1.0, np.quantile(texture, 1 - CLIPPED))
texture /= fit
print(f"scaled down by {fit:.3f} to fit")

# Resampled to the texture's grid, each texel's middle at its planetocentric latitude and longitude,
# 0 degrees in the middle column, in linear light. Cassini's grid holds its values at whole steps.
w, h = SIZE
pad = 4
padded = np.concatenate([texture[:, -pad:], texture, texture[:, :pad]], axis=1)
row = (np.arange(h) + 0.5) * 180 / h / CASSINI_STEP
column = ((np.arange(w) + 0.5) * 360 / w - 180) % 360 / CASSINI_STEP + pad
rr, cc = np.meshgrid(row, column, indexing='ij')
img = np.stack([ndimage.map_coordinates(padded[..., c], [rr, cc], order=3, mode='nearest') for c in range(3)], axis=-1)
pixels = (np.clip(img, 0, 1) * 65535 + 0.5).astype('<u2')
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '16', '-endian', 'LSB', 'rgb:-', '-set', 'colorspace', 'RGB',
                '-colorspace', 'sRGB', '-depth', '8', '-define', 'png:exclude-chunks=date,time', out],
               input=pixels.tobytes(), check=True)
print('wrote', out)

# For haze.py: an I/F of 1 in each filter in the texture's linear sRGB, as a place whose albedo in a
# filter is the spectrum's there adds that filter's share of the spectrum, at the texture's scale, with
# the key light's blue divided out as the texture's is, since the sun lights the haze as it lights the
# disk.
key_light = np.array([1.0, 1.0, 1.0 / key_blue])
colours = {name: (scale / fit * each * key_light).tolist()
           for name, each in zip(cassini.FILTERS, tc.filter_colours(lam, albedo, M, list(cassini.FILTERS.values())))}
with open(os.path.join(data, 'colour.json'), 'w') as f:
    json.dump({'about': "Saturn's I/F in each of Cassini's filters as the texture's linear sRGB, its blue divided by "
                        "the key light's: a row for each filter.", 'colours': colours}, f, indent=1)
print("the texture's linear sRGB for an I/F of 1 in each filter:", {name: np.round(c, 5).tolist() for name, c in colours.items()})
