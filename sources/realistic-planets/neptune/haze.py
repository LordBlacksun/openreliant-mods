"""Fits a model of Neptune's haze to Voyager 2's frames of its limb at high phase, for the mod's
`neptune.glsl`, and prints the shader's numbers.

    python3 haze.py data haze.json

The frames (`haze.json`):

- Close: the wide-angle camera's Blue, Green and Orange frames of a stretch of the limb at 152
  degrees of phase, about 7 km a pixel, an hour and a half after closest approach.
- Clear: the narrow-angle camera's Clear frames of the same stretch minutes later, about 1 km a
  pixel, and of the limb at 136 degrees twelve hours after closest approach, about 6 km a pixel.
  The cameras looked at the limb from close by, so Neptune's centre is out of these frames.
- The departure sets at 133 degrees, six days later, about 70 km a pixel, show the whole crescent
  but don't resolve the haze, which lies within a pixel or two of the edge there: they are for
  checking what the game draws, not for the fit.

The geometry: at 152 degrees the camera stood about five of Neptune's radii from its middle, so it
saw the edge 12 degrees off the middle's direction, at a phase angle of its own. Each stretch's
geometry is worked out from the camera's place (`sight`), and a pixel's size at the edge from the
camera's distance to the edge (`km_per_pixel`). The frames at 136 degrees, from 32 radii, are close
to a view from afar.

The measurements:

- Each frame's limb is a circle fitted to its half-maximum edge: where, along each ray from the
  circle's centre, the brightness falls to half way between the peak just inside it and the sky
  just outside. The first guess is a circle through the bright crescent's peak, just inside the
  limb (`edge_guess`).
- The limb is cut into `SEGMENTS` stretches, and in each the frame's I/F is averaged in bins of
  height above the edge.
- The cameras' pointing isn't archived, so each stretch's angle round from the sun's direction comes
  from the lit crescent inside it (`crescent_angle`): the sun's cosine on the disk falls to 0 at the
  terminator, the nearer the edge the further the stretch is from the sun's direction. Minnaert's
  law with the texture's exponent for the filter (`EXPONENT`), a brightness and a floor of stray
  light is fitted to the stretch's I/F from `INSIDE` km inside the edge, below the haze, and gives
  the angle. The haze's light alone hardly tells the angle: while the sun stands well above the
  haze, its light falls off with height alike.
- The model takes each stretch's edge as a view from afar would show it, at the phase angle there and
  with the sun as high above it (`from_afar`).

The model (`scattering.py`), which the shader works out for each pixel in the same way: one main
haze, its extinction falling exponentially with height, the same all round Neptune, which stands for
the gas and the haze together. Its phase function is a Henyey-Greenstein lobe, taking `share` of the
light, and Rayleigh's, the gas's. The light scattered more than once is an estimate
(`scattering.multiple_light`), whose numbers come from a Monte Carlo of all orders of scattering in
the fitted haze (`multiple.py`, `estimate`). The camera blurs each frame by a Gaussian of `BLUR`
pixels, and its stray light lifts the sky: an exponential tail in height, with its own length, and
a constant, in each frame.

The fit, by least squares over the heights where the haze stands out from the stray light
(`FITTED`), each bin weighted by `RELATIVE` of its I/F plus `ABSOLUTE`:

- The phase function's lobe and share are shared by every filter: Clear at 152 and 136 degrees
  sets them, the only filter seen at two phases.
- Each filter has its own extinction, scale height and single-scattering albedo.
- Each frame has its own stray light. The edges of the frames past `SPHERE_PHASE` degrees, at 152,
  are the game's sphere; a frame's at 136 degrees may stand `MOST_SHIFT` km off.
- The fit runs in `FIT_ROUNDS` rounds. The first fits the haze alone; after each, a Monte Carlo of
  the fitted haze gives the estimate's numbers, and the next round fits the haze again with them.
- It prints each round's estimate, each filter's numbers, each frame's own, and the haze for
  `neptune.glsl` (`scattering.constructor`), in the order blue, green, orange, with the matrix that
  turns the three filters' I/F into the texture's linear sRGB (`data/colour.json`, which
  `compose.py` writes).
"""
import json
import multiprocessing
import os
import sys

import numpy as np
from scipy import ndimage, optimize, sparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import globe  # noqa: E402
import multiple  # noqa: E402
import scattering  # noqa: E402
import voyager  # noqa: E402

# Neptune's equatorial radius, km (IAU): the game's sphere.
UNIT = 24764.0
# The measurements: the stretches of limb in a frame, and the heights binned, km above the edge.
SEGMENTS = 3
HEIGHTS = (-300.0, 400.0)
# The crescent: the depths its light is fitted over, km inside the edge, in bins of `CRESCENT_STEP`
# km or a pixel; Minnaert's exponent in each filter, as the texture's fit has it
# (neptune-voyager-map.pdf, Table 2), and the least cosine of the view; and the angles from the
# sun's direction the fit starts from, degrees, the best of which it keeps.
INSIDE = (150.0, 3000.0)
CRESCENT_STEP = 5.0
EXPONENT = {'Clear': 0.752, 'Blue': 0.768, 'Green': 0.712, 'Orange': 0.680}
LEAST_MU = 0.25
ANGLE_STARTS = (5.0, 35.0, 65.0, 80.0)
# A frame's data: the pixels left out round a gap, the jump of a row's median that marks it as
# garbage, and the least I/F that holds data, which the sky's noise stays well above.
MARGIN = 10
ROW_JUMP = 0.02
LEAST_IOF = -0.05
# The edge's first guess: in each column and each row, the brightest pixel where it is brighter than
# `RIDGE` of the brightest, which lies on the peak just inside the limb, and a circle through them
# that `RANSAC_TRIALS` trials find, within `RANSAC_NEAR` pixels.
RIDGE = 0.4
RANSAC_TRIALS = 3000
RANSAC_NEAR = 3.0
# The edge's fit: along rays from the centre, the peak within `PEAK_REACH` pixels inside the circle,
# the sky between `SKY_REACH` pixels outside, and the fit repeated `EDGE_FITS` times.
PEAK_REACH = 60
SKY_REACH = (30, 60)
EDGE_FITS = 3
# How far each fit may move the circle's centre and change its radius, as a share of the radius.
EDGE_FREEDOM = 0.05
# The model: the height the extinction is given at, km above `UNIT`; the height the haze is cut off
# at, where its extinction is a hundred-millionth of the edge's or less; the steps along a line of
# sight, closest where it passes nearest Neptune; and the camera's blur, pixels.
REFERENCE = 100.0
TOP = 300.0
STEPS, SPREAD = 96, 3.0
BLUR = 0.7
# The fit: the heights fitted, km above the edge; each bin's weight; how far a 136-degree frame's
# edge may stand off the game's sphere, km; the least pixels a bin needs; and the most evaluations.
FITTED = (-10.0, 250.0)
RELATIVE, ABSOLUTE = 0.05, 1e-3
MOST_SHIFT = 300.0
LEAST_PIXELS = 6
MOST_EVALUATIONS = 1500
# The filters, their own numbers, first guesses and bounds: the extinction at `REFERENCE` (its
# logarithm, per km), the scale height (km) and the single-scattering albedo.
FILTERS = ['Clear', 'Blue', 'Green', 'Orange']
OWN_FILTER = ['log extinction', 'scale height', 'albedo']
FILTER_FIRST_GUESS = [np.log(2e-3), 30.0, 0.9]
FILTER_LOWEST = [-25.0, 5.0, 0.05]
FILTER_HIGHEST = [3.0, 150.0, 1.0]
# The phase function's lobe's asymmetry and share, shared by every filter.
SHARED = ['lobe', 'share']
SHARED_FIRST_GUESS = [0.6, 0.5]
SHARED_LOWEST = [0.0, 0.0]
SHARED_HIGHEST = [0.97, 1.0]
# The least phase angle of the frames whose edges are the game's sphere, degrees.
SPHERE_PHASE = 145.0
# Each frame's own: its edge's shift (km), its stray light's tail and the tail's length (km), and a
# constant; the first guesses and bounds of the tail and the constant. The camera's stray light
# spreads over tens of pixels, so the tail is at least `SHORTEST_TAIL` pixels and `SHORTEST_TAIL_KM`
# long, and can't stand in for the haze, which falls off within a few.
OWN_FRAME = ['shift', 'tail', 'length', 'offset']
FRAME_FIRST_GUESS = [1e-2, 0.0]
FRAME_LOWEST = [0.0, -0.05]
FRAME_HIGHEST = [0.5, 0.2]
SHORTEST_TAIL = 30.0
SHORTEST_TAIL_KM = 100.0
LONGEST_TAIL_KM = 3000.0
# The light scattered more than once (`multiple.py`): the rounds of the fit, each after the first
# fitting the haze with the estimate the last round's haze gave; the Monte Carlo's heights above
# `UNIT`, km, and its paths for each line; and how far below `UNIT` its paths end, km, in haze far
# too deep for sunlight to reach.
FIT_ROUNDS = 3
MULTIPLE_HEIGHTS = np.array([2.0, 6.0, 12.0, 20.0, 30.0, 45.0, 60.0, 80.0, 110.0, 150.0])
MULTIPLE_PATHS = 20000
FLOOR = 200.0
# How much of the haze's light blooms, which the mod chooses rather than the fit: a quarter, as for
# Titan's.
BLOOM = 0.25


def frame(data, f):
    """A frame's I/F, NaN where it holds no data: a block of exact zeros, which the sky's noise
    rarely gives, I/F below `LEAST_IOF`, which some frames hold outside the camera's own frame, both
    with `MARGIN` pixels round them, and a row whose median jumps far from its neighbours', which
    the rows at a gap's edge hold."""
    image, _ = voyager.image(os.path.join(data, f['name'] + '_GEOMED.IMG'), os.path.join(data, f['name'] + '_GEOMED.LBL'))
    gap = (ndimage.minimum_filter((image == 0).astype(np.uint8), size=7) == 1) | (image < LEAST_IOF)
    gap = ndimage.binary_dilation(gap, iterations=MARGIN) | ~np.isfinite(image)
    rows = np.median(np.where(gap, 0.0, image), axis=1)
    jumps = np.abs(rows - ndimage.median_filter(rows, 9)) > ROW_JUMP
    return np.where(gap | ndimage.binary_dilation(jumps, iterations=3)[:, None], np.nan, image)


def km_per_pixel(f, data):
    """A frame's pixel at Neptune's edge, km: the pixel's angle times the camera's distance from the
    edge, which is less than its distance from the middle."""
    fields = voyager.label(os.path.join(data, f['name'] + '_GEOMED.LBL'))
    return np.sqrt(f['distance_km'] ** 2 - UNIT ** 2) * voyager.pixel(fields)


def edge_guess(image, radius):
    """A first guess at the limb's circle, pixels: through the brightest pixel of each column and
    each row, which lies on the peak just inside the limb, the circle of about `radius` that most of
    them lie on."""
    # Hot pixels and cosmic rays out first.
    smooth = ndimage.gaussian_filter(ndimage.median_filter(np.nan_to_num(image), 5), 2)
    least = RIDGE * np.percentile(smooth, 99.5)
    points = []
    for x in range(20, image.shape[1] - 20, 4):
        y = int(np.argmax(smooth[20:-20, x])) + 20
        if smooth[y, x] > least:
            points.append((x, y))
    for y in range(20, image.shape[0] - 20, 4):
        x = int(np.argmax(smooth[y, 20:-20])) + 20
        if smooth[y, x] > least:
            points.append((x, y))
    points = np.array(points, dtype=float)
    rng = np.random.default_rng(0)
    best, best_count = None, 0
    for _ in range(RANSAC_TRIALS):
        # Three points in a line give no circle, and a radius that is NaN, which the test below drops.
        with np.errstate(invalid='ignore'):
            cx, cy, r = globe.circle(points[rng.choice(len(points), 3, replace=False)])
        if not 0.7 * radius < r < 1.4 * radius:
            continue
        count = int((np.abs(np.hypot(points[:, 0] - cx, points[:, 1] - cy) - r) < RANSAC_NEAR).sum())
        if count > best_count:
            best, best_count = (cx, cy, r), count
    return best


def edge_fit(image, guess):
    """The limb's circle fitted to its half-maximum edge, and the edge's points and the angles they
    stand at from the centre."""
    cx, cy, r = guess
    clean = np.nan_to_num(image, nan=-1.0)
    for _ in range(EDGE_FITS):
        angles = np.linspace(-np.pi, np.pi, 3600, endpoint=False)
        offsets = np.arange(-PEAK_REACH, SKY_REACH[1] + 1, 0.25)
        points = []
        for a in angles:
            rr = r + offsets
            xs, ys = cx + rr * np.cos(a), cy - rr * np.sin(a)
            if xs.min() < 5 or ys.min() < 5 or xs.max() > image.shape[1] - 6 or ys.max() > image.shape[0] - 6:
                continue
            ray = ndimage.map_coordinates(clean, [ys, xs], order=1)
            if (ray < -0.5).any():
                continue
            inside = offsets <= 0
            peak = ray[inside].max()
            sky = np.median(ray[(offsets >= SKY_REACH[0]) & (offsets <= SKY_REACH[1])])
            half = sky + 0.5 * (peak - sky)
            if peak - sky < 0.05:
                continue
            after = np.nonzero((np.arange(len(ray)) > np.argmax(np.where(inside, ray, -1))) & (ray < half))[0]
            if len(after) == 0:
                continue
            i = after[0]
            e = rr[i - 1] + (ray[i - 1] - half) / (ray[i - 1] - ray[i]) * (rr[i] - rr[i - 1])
            points.append((cx + e * np.cos(a), cy - e * np.sin(a)))
        points = np.array(points).reshape(-1, 2)
        # A short stretch of limb pins its curvature weakly, so the circle stays near the guess.
        result = optimize.least_squares(lambda p: np.hypot(points[:, 0] - p[0], points[:, 1] - p[1]) - p[2], [cx, cy, r], loss='soft_l1',
                                        bounds=([cx - EDGE_FREEDOM * r, cy - EDGE_FREEDOM * r, (1 - EDGE_FREEDOM) * r],
                                                [cx + EDGE_FREEDOM * r, cy + EDGE_FREEDOM * r, (1 + EDGE_FREEDOM) * r]))
        cx, cy, r = result.x
    angles = np.arctan2(-(points[:, 1] - cy), points[:, 0] - cx)
    return (cx, cy, r), points, angles, float(np.sqrt(np.mean(result.fun ** 2)))


def binned(image, height, inside, bins):
    """The I/F of the pixels `inside` averaged in bins of their `height`, the bins' middles, and the
    pixels in each."""
    rows = np.digitize(height[inside], bins) - 1
    total = np.bincount(rows, weights=image[inside], minlength=len(bins) - 1)
    count = np.bincount(rows, minlength=len(bins) - 1)
    with np.errstate(invalid='ignore'):
        return (bins[:-1] + bins[1:]) / 2, total / count, count


def sight(distance, phase, angle, depth):
    """The line of sight of a camera `distance` km from Neptune's middle, at `phase` degrees, through
    the disk `depth` km inside the edge, as `km_per_pixel` measures it there, `angle` degrees round
    from the sun's direction: where it meets the sphere, in Neptune's radii from the middle, its
    direction, and the sun's. The camera stands on the z axis, looking toward the middle, and the
    sun's direction across the sky is along x."""
    d = distance / UNIT
    a, p = np.radians(phase), np.radians(angle)
    off_middle = np.arcsin(1 / d) - np.atleast_1d(depth) / np.sqrt(distance ** 2 - UNIT ** 2)
    line = np.stack([np.sin(off_middle) * np.cos(p), np.sin(off_middle) * np.sin(p), -np.cos(off_middle)], axis=-1)
    reach = d * np.cos(off_middle) - np.sqrt(np.clip(1 - (d * np.sin(off_middle)) ** 2, 0, None))
    return np.array([0.0, 0.0, d]) + reach[:, None] * line, line, np.array([np.sin(a), 0.0, np.cos(a)])


def crescent(depth, angle, phase, distance, k):
    """Minnaert's law's factor, mu0^k mu^(k-1), with exponent `k`, at `depth` km inside the edge of
    a stretch `angle` degrees round from the sun's direction, seen by a camera `distance` km from the
    middle at `phase` degrees, the view's cosine held at `LEAST_MU`."""
    point, line, sun = sight(distance, phase, angle, depth)
    mu0, mu = point @ sun, -np.sum(line * point, axis=1)
    return np.clip(mu0, 0, None) ** k * np.maximum(mu, LEAST_MU) ** (k - 1)


def crescent_angle(depth, mean, phase, distance, k):
    """A stretch's angle round from the sun's direction, degrees: where Minnaert's law, with a
    brightness and a floor fitted along with it, best follows the crescent's I/F `mean` at `depth` km
    inside the edge, seen by a camera `distance` km from the middle at `phase` degrees."""
    def residuals(p):
        brightness, floor, angle = p
        return (brightness * crescent(depth, angle, phase, distance, k) + floor - mean) / (RELATIVE * np.abs(mean) + ABSOLUTE)

    fits = [optimize.least_squares(residuals, [0.5, 0.0, start], bounds=([0.0, -0.1, 0.0], [3.0, 0.2, 89.9])) for start in ANGLE_STARTS]
    return min(fits, key=lambda fit: fit.cost).x[2]


def from_afar(distance, phase, angle):
    """The edge that a camera `distance` km from Neptune's middle, at `phase` degrees, sees `angle`
    degrees round from the sun's direction, as a view from afar shows it, which the haze's model
    takes: the phase angle at the edge, and the angle round from the sun's direction that sets the
    sun as high above it, degrees. The line of sight crosses the haze in the same way in both."""
    point, line, sun = sight(distance, phase, angle, 0.0)
    there = np.arccos(np.clip(-line[0] @ sun, -1, 1))
    return np.degrees(there), np.degrees(np.arccos(np.clip(point[0] @ sun / np.sin(there), -1, 1)))


def measure(data, f):
    """A frame's limb, in `SEGMENTS` stretches: each one's I/F averaged in bins of height above the
    edge, with the pixels in each bin, its angle round from the sun's direction, and its edge as a
    view from afar shows it (`from_afar`)."""
    image = frame(data, f)
    km = km_per_pixel(f, data)
    guess = edge_guess(image, UNIT / km)
    (cx, cy, r), points, angles, rms = edge_fit(image, guess)
    lines, samples = np.indices(image.shape).astype(np.float64)
    x, y = samples - cx, cy - lines
    height = (np.hypot(x, y) - r) * km
    # The stretches: the middle of the edge's span, round from its middle.
    middle = np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))
    spread = np.angle(np.exp(1j * (angles - middle)))
    low, high = np.percentile(spread, [10, 90])
    turn = np.angle(np.exp(1j * (np.arctan2(y, x) - middle)))
    bins = np.arange(HEIGHTS[0], HEIGHTS[1] + km, max(km, 2.0))
    inward = np.arange(-INSIDE[1], -INSIDE[0] + 1e-6, max(km, CRESCENT_STEP))
    stretches = []
    for k in range(SEGMENTS):
        start, end = low + (high - low) * k / SEGMENTS, low + (high - low) * (k + 1) / SEGMENTS
        along = np.isfinite(image) & (turn >= start) & (turn < end)
        heights, mean, count = binned(image, height, along & (height >= bins[0]) & (height < bins[-1]), bins)
        depth, light, seen = binned(image, height, along & (height >= inward[0]) & (height < inward[-1]), inward)
        used = (seen >= LEAST_PIXELS) & np.isfinite(light)
        angle = crescent_angle(-depth[used], light[used], f['phase'], f['distance_km'], EXPONENT[f['filter']])
        phase, afar = from_afar(f['distance_km'], f['phase'], angle)
        stretches.append(dict(heights=heights, mean=mean, count=count, angle=afar, phase=phase, round=angle))
    print(f"{f['name']} ({f['filter']}, {f['phase']:.1f} degrees, {km:.2f} km a pixel): edge rms {rms:.2f} px over "
          f"{len(points)} points; stretches " + ', '.join(f"{s['round']:.1f}" for s in stretches) + " degrees round from the sun's "
          "direction, at " + ', '.join(f"{s['phase']:.1f}" for s in stretches) + " degrees of phase")
    return dict(name=f['name'], filter=f['filter'], phase=f['phase'], km=km, stretches=stretches)


def haze_of(own_filter, shared):
    """A filter's haze as the model and the Monte Carlo take it (`multiple.Haze`): one lobe and
    Rayleigh's."""
    log_extinction, scale, albedo = own_filter
    lobe, share = shared
    return multiple.Haze(UNIT + REFERENCE, log_extinction, scale, albedo, (lobe, 0.0, share, 0.0), UNIT + TOP, UNIT - FLOOR)


def stretch_iof(heights, angle, phase, own_filter, shared, more=None):
    """The haze's I/F at `heights` km above `UNIT` across the limb at `angle` degrees round from the
    sun's direction, seen from afar at `phase` degrees (`scattering.iof`), and with `more`, the
    estimate's numbers, the light scattered more than once."""
    body = haze_of(own_filter, shared)
    a = np.radians(angle)
    r = UNIT + heights
    return scattering.iof(r * np.cos(a), r * np.sin(a), phase, body.reference, body.log_extinction, body.scale, body.albedo,
                          body.lobes, body.top, STEPS, SPREAD, multiple=more)


def estimate(own_filter, shared, seed):
    """The estimate's numbers for the light a filter's fitted haze scatters more than once, fitted
    to a Monte Carlo of it, and how far the Monte Carlo's lines are from them."""
    return multiple.estimate(haze_of(own_filter, shared), MULTIPLE_HEIGHTS, UNIT, MULTIPLE_PATHS, seed, STEPS, SPREAD)


def fit(measured, more):
    """The shared numbers, each filter's, and each frame's own, fitted to the stretches, with `more`,
    each filter's numbers for the light scattered more than once, or none."""
    data, weights, rows_of = [], [], []
    for m in measured:
        for s in m['stretches']:
            rows = (s['heights'] >= FITTED[0]) & (s['heights'] <= FITTED[1])
            mean, count = s['mean'][rows], s['count'][rows]
            ok = np.isfinite(mean) & (count >= LEAST_PIXELS)
            data.append(np.where(ok, mean, 0))
            weights.append(np.where(ok, 1 / (RELATIVE * np.abs(np.where(ok, mean, 0)) + ABSOLUTE), 0))
            rows_of.append(rows)
    shared_count, filter_count = len(SHARED), len(OWN_FILTER)
    frame_start = shared_count + filter_count * len(FILTERS)

    def split(p):
        shared = p[:shared_count]
        filters = {f: p[shared_count + i * filter_count:shared_count + (i + 1) * filter_count] for i, f in enumerate(FILTERS)}
        frames = [p[frame_start + i * len(OWN_FRAME):frame_start + (i + 1) * len(OWN_FRAME)] for i in range(len(measured))]
        return shared, filters, frames

    def model(m, s, rows, shared, own_filter, own):
        shift, tail, length, offset = own
        # The heights fitted, and a margin round them for the blur.
        step = s['heights'][1] - s['heights'][0]
        sigma = BLUR * m['km'] / step
        margin = int(np.ceil(4 * sigma)) + 1
        index = np.nonzero(rows)[0]
        near = slice(max(index[0] - margin, 0), min(index[-1] + margin + 1, len(rows)))
        heights = s['heights'][near]
        iof = stretch_iof(heights + shift, s['angle'], s['phase'], own_filter, shared, more[m['filter']])
        iof = ndimage.gaussian_filter1d(iof, sigma, mode='nearest')
        sky = offset + tail * np.exp(-np.clip(heights, 0, None) / length)
        return (iof + sky)[rows[near]]

    def residuals(p):
        shared, filters, frames = split(p)
        out, k = [], 0
        for m, own in zip(measured, frames):
            for s in m['stretches']:
                out.append(((model(m, s, rows_of[k], shared, filters[m['filter']], own) - data[k]) * weights[k]).ravel())
                k += 1
        return np.concatenate(out)

    start = list(SHARED_FIRST_GUESS) + FILTER_FIRST_GUESS * len(FILTERS)
    lowest = list(SHARED_LOWEST) + FILTER_LOWEST * len(FILTERS)
    highest = list(SHARED_HIGHEST) + FILTER_HIGHEST * len(FILTERS)
    for m in measured:
        # The bounds must stand apart, so an edge on the game's sphere is held within a hair of it.
        shift = 1e-6 if m['phase'] > SPHERE_PHASE else MOST_SHIFT
        shortest = max(SHORTEST_TAIL * m['km'], SHORTEST_TAIL_KM)
        start += [0.0, FRAME_FIRST_GUESS[0], 2 * shortest, FRAME_FIRST_GUESS[1]]
        lowest += [-shift, FRAME_LOWEST[0], shortest, FRAME_LOWEST[1]]
        highest += [shift, FRAME_HIGHEST[0], LONGEST_TAIL_KM, FRAME_HIGHEST[1]]
    # Each stretch's residuals hang on the shared numbers, its filter's and its frame's alone.
    sparsity = sparse.lil_matrix((sum(d.size for d in data), len(start)), dtype=int)
    row, k = 0, 0
    for i, m in enumerate(measured):
        f = FILTERS.index(m['filter'])
        for _ in m['stretches']:
            size = data[k].size
            sparsity[row:row + size, :shared_count] = 1
            sparsity[row:row + size, shared_count + f * filter_count:shared_count + (f + 1) * filter_count] = 1
            sparsity[row:row + size, frame_start + i * len(OWN_FRAME):frame_start + (i + 1) * len(OWN_FRAME)] = 1
            row += size
            k += 1
    result = optimize.least_squares(residuals, start, bounds=(lowest, highest), jac_sparsity=sparsity, x_scale='jac',
                                    max_nfev=MOST_EVALUATIONS)
    return split(result.x), result


if __name__ == '__main__':
    data, listing = sys.argv[1:3]
    with open(listing) as f:
        frames = [frame_ for frame_ in json.load(f)['frames'] if frame_['role'] in ('close', 'clear')]
    with open(os.path.join(data, 'colour.json')) as f:
        colours = json.load(f)['colours']
    # The phase the texture shows Neptune at: the mean of its frames', `frames.json`'s.
    with open(os.path.join(os.path.dirname(os.path.abspath(listing)), 'frames.json')) as f:
        texture_phase = np.mean([frame_['phase'] for frame_ in json.load(f)['frames']])
    measured = [measure(data, f) for f in frames]
    # The first round fits the haze alone; each after it, with the estimate the last round's haze gave.
    more = {name: None for name in FILTERS}
    with multiprocessing.Pool(len(FILTERS)) as pool:
        for fit_round in range(FIT_ROUNDS):
            (shared, filters, owns), result = fit(measured, more)
            if fit_round == FIT_ROUNDS - 1:
                break
            estimates = pool.starmap(estimate, [(filters[name], shared, seed) for seed, name in enumerate(FILTERS)])
            more = {name: numbers for name, (numbers, off) in zip(FILTERS, estimates)}
            for name, (numbers, off) in zip(FILTERS, estimates):
                print(f"round {fit_round + 1}, {name}: {multiple.describe(numbers, off)}")
    print(f"fit: cost {result.cost:.3g} after {result.nfev} evaluations")
    print('shared: ' + ', '.join(f'{k} {v:.4g}' for k, v in zip(SHARED, shared)))
    for name in FILTERS:
        print(f"{name}: " + ', '.join(f'{k} {v:.4g}' for k, v in zip(OWN_FILTER, filters[name])))
    for m, own in zip(measured, owns):
        print(f"  {m['name']} ({m['filter']}, {m['phase']:.1f} degrees): " + ', '.join(f'{k} {v:.4g}' for k, v in zip(OWN_FRAME, own)))
    colour_filters = ['Blue', 'Green', 'Orange']
    numbers = np.array([filters[name] for name in colour_filters]).T
    lobe, share = shared
    # One lobe and Rayleigh's, and no detached layer, whose extinction is 0.
    print('for neptune.glsl:')
    print(scattering.constructor(
        'neptuneHaze', UNIT, UNIT + REFERENCE, UNIT + TOP, np.exp(numbers[0]), numbers[1], [0.0] * 3, [UNIT] * 3, [1.0] * 3,
        -np.cos(np.radians(texture_phase)), numbers[2], [lobe] * 3, [0.0] * 3, [share] * 3, [0.0] * 3,
        [more[name] for name in colour_filters], [colours[name] for name in colour_filters], BLOOM))
