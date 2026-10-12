"""Fits a model of Titan's haze beyond its disk to Cassini's frames, for the mod's `titan.glsl`, and
prints the shader's numbers. Run `compose.py` first: it writes `data/colour.json`, which turns
the haze's I/F into the texture's colours.

    python3 haze.py data frames.json haze.json

The frames:

- `frames.json`'s twelve frames, at phase angles of 28 to 50 degrees, which `compose.py` makes the
  texture from, and `haze.json`'s 33: eleven sets in the blue, green and red filters from February
  2009 to August 2010, around Titan's equinox, at phase angles of 140 to 164 degrees. With the sun
  behind Titan, the haze scatters the sunlight toward the camera and shows as a bright ring round the
  dark disk, and above it the detached haze layer as a fainter one.
- The sun's direction in each frame comes from the frame's geometry (`cassini.axes`).
- A low-phase frame's disk is fitted to its lit limb as `compose.py` fits it (`cassini.limb`), so
  that heights here match the texture's edges. A high-phase frame has no lit disk: its centre is
  fitted to the outer edge of the ring on the sun's side, where the brightness along each ray falls to
  a quarter of its peak, and the fit below moves it further where the model needs.
- Each frame's sky, the median more than `SKY_FROM` km beyond `BASE`, is taken off, and its I/F is
  averaged in bins of height above `BASE` and of angle from the sun's direction.

The model (`scattering.py`), which the shader works out for each pixel in the same way:

- In each filter, the extinction is the main haze's, falling exponentially with height above `BASE`,
  and the detached layer's, a Gaussian in height. Both are the same all round Titan. The detached
  layer is optically thin, and is left out of the sunlight's depth.
- The phase function is the sum of two Henyey-Greenstein lobes, the first taking `share` of the
  light.
- The light scattered more than once is an estimate (`scattering.multiple_light`): a beam of
  sunlight scattered forward again on its way to the camera, and a glow of light scattered many
  times. Its numbers come from a Monte Carlo of all orders of scattering in the fitted haze, whose
  paths end at Titan's solid surface (`multiple.py`, `estimate`).
- The camera blurs each frame by a Gaussian of `BLUR` pixels, and its stray light lifts the sky round
  the bright disk and ring: an exponential tail in height, with its own length, and a constant, in
  each frame.

The fit:

- Each filter is fitted on its own, by least squares, to the heights where the haze stands out from
  the stray light (`FITTED`), each bin weighted by `RELATIVE` of its I/F plus `ABSOLUTE`. The haze's
  numbers are shared by all the filter's frames; the stray light, and each high-phase frame's centre,
  within `MOST_SHIFT` km, are each frame's own.
- The fit runs in `FIT_ROUNDS` rounds. The first fits the haze alone; after each, a Monte Carlo of
  the fitted haze gives the estimate's numbers, and the next round fits the haze again with them.
- It prints each round's estimate, each filter's numbers, each frame's own, and the haze for
  `titan.glsl` (`scattering.constructor`), in the order blue, green, red, with the matrix that turns
  the three filters' I/F into the texture's linear sRGB (`data/colour.json`) and the cosine of the
  scattering angle at the mean phase of the texture's frames.
"""
import json
import multiprocessing
import os
import sys

import numpy as np
from scipy import ndimage, optimize, sparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import cassini  # noqa: E402
import globe  # noqa: E402
import multiple  # noqa: E402
import scattering  # noqa: E402

# Heights are measured from `BASE` km from Titan's centre, about the haze's edge in red, and the haze
# is cut off `TOP` km above it. The game's sphere is `UNIT` km: the haze's edge in green, where the
# texture's disk ends (`compose.py`). The main haze's extinction is given `REFERENCE` km above `BASE`.
BASE = 2710.0
TOP = 700.0
UNIT = 2741.0
REFERENCE = 100.0
# The bins: heights above `BASE`, km, and angles from the sun's direction, degrees.
HEIGHT_BINS = np.arange(-200.0, 801.0, 8.0)
ANGLE_BINS = np.arange(-180.0, 181.0, 10.0)
# The sky is the median more than `SKY_FROM` km beyond `BASE`.
SKY_FROM = 1100.0
# A high-phase frame's ring: rays within `RING_SIDE` degrees of the sun's direction, from `RING_REACH`
# of the radius in `RING_SAMPLES` steps, its outer edge where the brightness falls to `RING_EDGE` of
# the ray's peak, and the fit repeated `RING_FITS` times. The first guess at the ring is the pixels
# brighter than `RING_GUESS` of the 99.5th percentile, `RING_RADIUS` km across.
RING_SIDE = 90.0
RING_REACH = (0.6, 1.5)
RING_SAMPLES = 451
RING_EDGE = 0.25
RING_FITS = 6
RING_GUESS = 0.3
RING_RADIUS = 2900.0
# The fit: the heights modelled, km above `BASE`, with a margin round those fitted for the blur; the
# heights fitted in a high-phase frame (True) and a low-phase one (False); the least pixels a bin
# needs; each bin's weight; how far a high-phase frame's centre may move, km; the camera's blur,
# pixels; and the most evaluations.
MODELLED = (0.0, 560.0)
FITTED = {True: (40.0, 380.0), False: (60.0, 260.0)}
LEAST_PIXELS = 6
RELATIVE, ABSOLUTE = 0.05, 3e-4
MOST_SHIFT = 120.0
BLUR = 0.6
MOST_EVALUATIONS = 200
# How much of the haze's light blooms, which the mod chooses rather than the fit: a quarter, as the
# bloom would spread the bright haze of a backlit Titan well past what Cassini saw.
BLOOM = 0.25
# The steps along a line of sight, closest where it passes nearest Titan.
STEPS, SPREAD = 96, 3.0
# The light scattered more than once (`multiple.py`): the rounds of the fit, each after the first
# fitting the haze with the estimate the last round's haze gave; the Monte Carlo's heights above
# the game's sphere, km, and its paths for each line; and the radius its paths end at, Titan's
# solid surface, km.
FIT_ROUNDS = 3
MULTIPLE_HEIGHTS = np.array([5.0, 20.0, 40.0, 60.0, 80.0, 100.0, 130.0, 170.0, 220.0, 290.0])
MULTIPLE_PATHS = 20000
SURFACE = 2575.0
# The haze's numbers, their first guesses and bounds: the main haze's extinction 100 km above `BASE`
# (its logarithm, per km) and scale height (km), the detached layer's peak extinction (its
# logarithm), height (km above `BASE`) and width (km), the single-scattering albedo, and the phase
# function's two lobes' asymmetries and the first's share.
NAMES = ['log extinction', 'scale height', 'log layer', 'layer height', 'layer width', 'albedo',
         'first lobe', 'second lobe', 'share']
FIRST_GUESS = [np.log(1.5e-3), 28.0, np.log(1e-5), 318.0, 32.0, 0.95, 0.75, -0.2, 0.9]
LOWEST = [-15.0, 10.0, -20.0, 250.0, 8.0, 0.3, 0.2, -0.8, 0.3]
HIGHEST = [2.0, 120.0, -5.0, 380.0, 80.0, 1.0, 0.97, 0.6, 1.0]
# Each frame's own: its centre's shift (km), its stray light's tail and the tail's length (km), and a
# constant; their first guesses, and their bounds, but for the shift's, which is `MOST_SHIFT` at high
# phase and none at low phase.
OWN = ['dx', 'dy', 'tail', 'length', 'offset']
OWN_FIRST_GUESS = [0.0, 0.0, 1e-3, 200.0, 0.0]
OWN_LOWEST = [0.0, 40.0, -3e-3]
OWN_HIGHEST = [0.05, 2000.0, 3e-3]


def sun_direction(f):
    """The sun's direction in a frame, radians from right toward up."""
    right, up, _, sun = cassini.axes(f)
    return np.arctan2(sun @ up, sun @ right)


def polar(image, cx, cy, radii, angles):
    """An image along rays from (`cx`, `cy`), NaN beyond its edges."""
    xs = cx + np.outer(np.cos(angles), radii)
    ys = cy - np.outer(np.sin(angles), radii)
    return ndimage.map_coordinates(image, [ys, xs], order=1, mode='constant', cval=np.nan)


def ring_centre(image, res, sun):
    """A high-phase frame's centre and radius, pixels: the ring's outer edge on the sun's side, along
    rays where the brightness falls to `RING_EDGE` of the ray's peak, and a circle through those
    points."""
    bright = image > RING_GUESS * np.percentile(image, 99.5)
    cy, cx = np.argwhere(bright).mean(axis=0)
    radius = RING_RADIUS / res
    angles = sun + np.radians(np.arange(-RING_SIDE, RING_SIDE + 0.1, 1.0))
    for _ in range(RING_FITS):
        radii = np.linspace(*RING_REACH, RING_SAMPLES) * radius
        rays = polar(image, cx, cy, radii, angles)
        peaks = np.nanmax(rays, axis=1)
        points = []
        for a, ray, peak in zip(angles, rays, peaks):
            if not peak > RING_EDGE * np.nanmax(peaks):
                continue
            i = np.nanargmax(ray)
            beyond = np.nonzero(ray[i:] < RING_EDGE * peak)[0]
            if len(beyond) == 0:
                continue
            j = i + beyond[0]
            edge = radii[j - 1] + (ray[j - 1] - RING_EDGE * peak) / (ray[j - 1] - ray[j]) * (radii[j] - radii[j - 1])
            points.append((cx + np.cos(a) * edge, cy - np.sin(a) * edge))
        cx, cy, radius = globe.circle(np.array(points))
    return cx, cy, radius


def binned(image, cx, cy, res, sun):
    """A frame's I/F averaged in bins of height and of angle from the sun, and the pixels in each."""
    lines, samples = np.indices(image.shape).astype(np.float64)
    x, y = samples - cx, cy - lines
    height = np.hypot(x, y) * res - BASE
    angle = (np.degrees(np.arctan2(y, x) - sun) + 180) % 360 - 180
    ok = np.isfinite(image) & (height >= HEIGHT_BINS[0]) & (height < HEIGHT_BINS[-1])
    rows = np.digitize(height[ok], HEIGHT_BINS) - 1
    columns = np.clip(np.digitize(angle[ok], ANGLE_BINS) - 1, 0, len(ANGLE_BINS) - 2)
    shape = (len(HEIGHT_BINS) - 1, len(ANGLE_BINS) - 1)
    index = rows * shape[1] + columns
    total = np.bincount(index, weights=image[ok], minlength=shape[0] * shape[1])
    count = np.bincount(index, minlength=shape[0] * shape[1])
    with np.errstate(invalid='ignore'):
        return (total / count).reshape(shape), count.reshape(shape)


def sky_level(image, cx, cy, res):
    """A frame's sky: the median more than `SKY_FROM` km beyond `BASE`."""
    lines, samples = np.indices(image.shape).astype(np.float64)
    far = np.isfinite(image) & (np.hypot(samples - cx, cy - lines) * res > BASE + SKY_FROM)
    return np.median(image[far]) if far.any() else 0.0


def prepare(data, frames, high):
    """Each frame's bins, with its filter, phase angle and resolution."""
    prepared = []
    for f in frames:
        # A pixel that can't be trusted is left out of the bins, but the sky's noise below zero is kept,
        # which `cassini.trusted` sets to zero for the limb fit.
        image = cassini.frame(os.path.join(data, os.path.basename(f['urls'][1])))
        image = np.where(np.isfinite(image) & (image < cassini.MOST_IF), image, np.nan)
        res, sun = f['resolution_km'], sun_direction(f)
        if high:
            cx, cy, radius = ring_centre(np.nan_to_num(image), res, sun)
        else:
            cx, cy, radius = cassini.limb(cassini.trusted(image), f)
        sky = sky_level(image, cx, cy, res)
        mean, count = binned(image - sky, cx, cy, res, sun)
        prepared.append(dict(name=f['name'], filter=f['filter'], phase=f['phase'], res=res, high=high, mean=mean, count=count))
        edge = "the ring's outer edge" if high else "the haze's edge"
        print(f"{f['name']} ({f['filter']}, {f['time'][:10]}, phase {f['phase']:.1f} degrees): centre ({cx:.1f}, {cy:.1f}), "
              f"{edge} {radius * res:.0f} km from it, sky {sky:+.5f}")
    return prepared


def layer_of(haze):
    """The detached layer's extinction as a function of the radius."""
    log_layer, layer_height, layer_width = haze[2:5]
    return lambda r: np.exp(log_layer - 0.5 * ((r - BASE - layer_height) / layer_width) ** 2)


def haze_of(haze):
    """The haze's numbers as the model and the Monte Carlo take them (`scattering.Haze`): two lobes
    and the detached layer."""
    log_extinction, scale, log_layer, layer_height, layer_width, albedo, first, second, share = haze
    return scattering.Haze(BASE + REFERENCE, log_extinction, scale, albedo, (first, second, share, 1 - share), BASE + TOP,
                           SURFACE, layer_of(haze))


def sky_iof(x, y, phase, haze, more=None):
    """The haze's I/F at sky points (x, y), km from Titan's centre, the sun's direction along x, seen
    from afar at `phase` degrees (`scattering.iof`), and with `more`, the estimate's numbers, the light
    scattered more than once."""
    return scattering.iof(x, y, phase, haze_of(haze), STEPS, SPREAD, more)


def estimate(haze, seed):
    """The estimate's numbers for the light the fitted haze scatters more than once, fitted to a
    Monte Carlo of it, and how far the Monte Carlo's lines are from them."""
    return multiple.estimate(haze_of(haze), MULTIPLE_HEIGHTS, UNIT, MULTIPLE_PATHS, seed, STEPS, SPREAD)


def fit_filter(frames, more):
    """The haze's numbers fitted to one filter's frames, with `more`, the estimate's numbers for the
    light scattered more than once, or none, and each frame's own."""
    heights = (HEIGHT_BINS[:-1] + HEIGHT_BINS[1:]) / 2
    angles = np.radians((ANGLE_BINS[:-1] + ANGLE_BINS[1:]) / 2)
    modelled = (heights > MODELLED[0]) & (heights < MODELLED[1])
    hh, aa = np.meshgrid(heights[modelled], angles, indexing='ij')
    data, weights, used = [], [], []
    for f in frames:
        low, high = FITTED[f['high']]
        rows = (heights[modelled] >= low) & (heights[modelled] <= high)
        mean, count = f['mean'][modelled][rows], f['count'][modelled][rows]
        ok = np.isfinite(mean) & (count >= LEAST_PIXELS)
        data.append(np.where(ok, mean, 0))
        weights.append(np.where(ok, 1 / (RELATIVE * np.abs(np.where(ok, mean, 0)) + ABSOLUTE), 0))
        used.append(rows)

    def model(f, haze, own):
        dx, dy, tail, length, offset = own
        m = sky_iof((BASE + hh) * np.cos(aa) - dx, (BASE + hh) * np.sin(aa) - dy, f['phase'], haze, more)
        m = ndimage.gaussian_filter1d(m, BLUR * f['res'] / (HEIGHT_BINS[1] - HEIGHT_BINS[0]), axis=0, mode='nearest')
        return m + tail * np.exp(-hh / length) + offset

    def split(p):
        return p[:len(NAMES)], [p[len(NAMES) + i * len(OWN):len(NAMES) + (i + 1) * len(OWN)] for i in range(len(frames))]

    def residuals(p):
        haze, owns = split(p)
        return np.concatenate([((model(f, haze, own)[rows] - d) * w).ravel() for f, own, rows, d, w in zip(frames, owns, used, data, weights)])

    start, lowest, highest = list(FIRST_GUESS), list(LOWEST), list(HIGHEST)
    for f in frames:
        # The bounds must stand apart, so a low-phase frame's shift is held within a hair of none.
        shift = (MOST_SHIFT if f['high'] else 0.0) + 1e-6
        start += OWN_FIRST_GUESS
        lowest += [-shift, -shift] + OWN_LOWEST
        highest += [shift, shift] + OWN_HIGHEST
    sparsity = sparse.lil_matrix((sum(d.size for d in data), len(start)), dtype=int)
    row = 0
    for i, d in enumerate(data):
        sparsity[row:row + d.size, :len(NAMES)] = 1
        sparsity[row:row + d.size, len(NAMES) + i * len(OWN):len(NAMES) + (i + 1) * len(OWN)] = 1
        row += d.size
    result = optimize.least_squares(residuals, start, bounds=(lowest, highest), jac_sparsity=sparsity, x_scale='jac',
                                    max_nfev=MOST_EVALUATIONS)
    return split(result.x)


if __name__ == '__main__':
    data, low_listing, high_listing = sys.argv[1:4]
    with open(os.path.join(data, 'colour.json')) as f:
        colours = json.load(f)['colours']
    frames = []
    for listing, high in [(low_listing, False), (high_listing, True)]:
        with open(listing) as f:
            frames += prepare(data, json.load(f)['frames'], high)
    # The phase the texture shows Titan at: the mean of its frames', the low-phase ones.
    with open(low_listing) as f:
        texture_phase = np.mean([frame['phase'] for frame in json.load(f)['frames']])
    order = sorted(cassini.FILTERS, key=cassini.FILTERS.get)
    by_filter = [[f for f in frames if f['filter'] == name] for name in order]
    # The first round fits the haze alone; each after it, with the estimate the last round's haze gave.
    more = [None] * len(order)
    with multiprocessing.Pool(len(order)) as pool:
        for fit_round in range(FIT_ROUNDS):
            fitted = dict(zip(order, pool.starmap(fit_filter, zip(by_filter, more))))
            if fit_round == FIT_ROUNDS - 1:
                break
            estimates = pool.starmap(estimate, [(fitted[name][0], seed) for seed, name in enumerate(order)])
            more = [numbers for numbers, off in estimates]
            for name, (numbers, off) in zip(order, estimates):
                print(f"round {fit_round + 1}, {name}: {multiple.describe(numbers, off)}")
    for name in order:
        haze, owns = fitted[name]
        print(f"{name}: " + ', '.join(f'{k} {v:.4g}' for k, v in zip(NAMES, haze)))
        for f, own in zip([f for f in frames if f['filter'] == name], owns):
            print(f"  {f['name']} at {f['phase']:.1f} degrees: " + ', '.join(f'{k} {v:.4g}' for k, v in zip(OWN, own)))
    haze = np.array([fitted[name][0] for name in order]).T
    # The fit stops a hair short of its bounds: a first lobe within a millionth of all the light takes
    # all of it.
    share = np.where(haze[8] > 1 - 1e-6, 1.0, haze[8])
    print('for titan.glsl:')
    print(scattering.constructor(
        'titanHaze', UNIT, BASE + REFERENCE, BASE + TOP, np.exp(haze[0]), haze[1], np.exp(haze[2]), BASE + haze[3], haze[4],
        -np.cos(np.radians(texture_phase)), haze[5], haze[6], haze[7], share, 1 - share, more, [colours[name] for name in order], BLOOM))
