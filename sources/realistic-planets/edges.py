"""A body's limb in frames that see a stretch of it, for the haze's fits (`neptune/haze.py`,
`saturn/haze.py`): the outline of its edge on a frame, the I/F in bins of height across it, where the
camera sees each stretch from, and the haze's numbers fitted to the stretches.

A flattened body's outline is an ellipse whose shape the frame's geometry gives: its short half-axis
as a share of its long one, and the long axis's angle from right toward up (`shape`). Points
stretched across that axis by the inverse of the share (`flattened`) see the outline as a circle,
which the fits use; a round body's shape is `ROUND`, which leaves points as they are.
"""
import numpy as np
from scipy import ndimage, optimize, sparse

import globe
import scattering

# The edge's first guess: in each column and each row, the brightest pixel where it is brighter than
# `RIDGE` of the brightest, which lies on the peak just inside the limb, and an outline through them,
# a circle once flattened, that `RANSAC_TRIALS` trials find, within `RANSAC_NEAR` pixels.
RIDGE = 0.4
RANSAC_TRIALS = 3000
RANSAC_NEAR = 3.0
# The edge's fit: along rays from the centre, the peak within `PEAK_REACH` pixels inside the outline,
# the sky between `SKY_REACH` pixels outside, and the fit repeated `EDGE_FITS` times.
PEAK_REACH = 60
SKY_REACH = (30, 60)
EDGE_FITS = 3
# How far each fit may move the outline's centre and change its size, as a share of its long
# half-axis.
EDGE_FREEDOM = 0.05
# A round body's outline: a share of 1, at no angle.
ROUND = (1.0, 0.0)


def flattened(x, y, shape):
    """Points `x` right and `y` up, pixels, stretched so that the outline of `shape` is a circle:
    along its long axis as they are, across it by the inverse of its share."""
    ratio, tilt = shape
    return x * np.cos(tilt) + y * np.sin(tilt), (y * np.cos(tilt) - x * np.sin(tilt)) / ratio


def unflattened(u, w, shape):
    """Points that `flattened` stretched, back where they were."""
    ratio, tilt = shape
    w = w * ratio
    return u * np.cos(tilt) - w * np.sin(tilt), u * np.sin(tilt) + w * np.cos(tilt)


def above(x, y, size, shape=ROUND):
    """How far points `x` right and `y` up of an outline's middle, pixels, stand outside the
    outline of `shape` whose long half-axis is `size` pixels, across it."""
    u, w = flattened(x, y, shape)
    stretched = np.hypot(u, w)
    # A step across the outline takes the stretched distance from the middle this much further.
    with np.errstate(invalid='ignore', divide='ignore'):
        rate = np.hypot(u, w / shape[0]) / stretched
    return (stretched - size) / rate


def edge_guess(image, radius, shape=ROUND):
    """A first guess at the limb's outline of `shape`, its centre and long half-axis, pixels:
    through the brightest pixel of each column and each row, which lies on the peak just inside the
    limb, the outline about `radius` across that most of them lie on."""
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
    points = np.stack(flattened(points[:, 0], -points[:, 1], shape), axis=1)
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
    cx, up = unflattened(best[0], best[1], shape)
    return cx, -up, best[2]


def edge_fit(image, guess, shape=ROUND):
    """The limb's outline of `shape` fitted to its half-maximum edge, its centre and long
    half-axis, and the edge's points and the angles they stand at from the centre."""
    cx, cy, r = guess
    clean = np.nan_to_num(image, nan=-1.0)
    angles = np.linspace(-np.pi, np.pi, 3600, endpoint=False)
    # How far the outline stands from its middle along each ray, as a share of its long half-axis.
    reach = 1 / np.hypot(*flattened(np.cos(angles), np.sin(angles), shape))
    for _ in range(EDGE_FITS):
        offsets = np.arange(-PEAK_REACH, SKY_REACH[1] + 1, 0.25)
        points = []
        for a, out in zip(angles, reach):
            rr = r * out + offsets
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
        # A short stretch of limb pins its curvature weakly, so the outline stays near the guess.
        result = optimize.least_squares(lambda p: above(points[:, 0] - p[0], p[1] - points[:, 1], p[2], shape), [cx, cy, r], loss='soft_l1',
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


def sight(unit, distance, phase, angle, depth):
    """The line of sight of a camera `distance` km from the middle of a sphere `unit` km across, at
    `phase` degrees, through the disk `depth` km inside the edge, as a pixel's size at the edge
    measures it there, `angle` degrees round from the sun's direction: where it meets the sphere, in
    radii from the middle, its direction, and the sun's. The camera stands on the z axis, looking
    toward the middle, and the sun's direction across the sky is along x."""
    d = distance / unit
    a, p = np.radians(phase), np.radians(angle)
    off_middle = np.arcsin(1 / d) - np.atleast_1d(depth) / np.sqrt(distance ** 2 - unit ** 2)
    line = np.stack([np.sin(off_middle) * np.cos(p), np.sin(off_middle) * np.sin(p), -np.cos(off_middle)], axis=-1)
    reach = d * np.cos(off_middle) - np.sqrt(np.clip(1 - (d * np.sin(off_middle)) ** 2, 0, None))
    return np.array([0.0, 0.0, d]) + reach[:, None] * line, line, np.array([np.sin(a), 0.0, np.cos(a)])


def from_afar(unit, distance, phase, angle):
    """The edge of a sphere `unit` km across that a camera `distance` km from its middle, at `phase`
    degrees, sees `angle` degrees round from the sun's direction, as a view from afar shows it,
    which the haze's model takes: the phase angle at the edge, and the angle round from the sun's
    direction that sets the sun as high above it, degrees. The line of sight crosses the haze in the
    same way in both."""
    point, line, sun = sight(unit, distance, phase, angle, 0.0)
    there = np.arccos(np.clip(-line[0] @ sun, -1, 1))
    return np.degrees(there), np.degrees(np.arccos(np.clip(point[0] @ sun / np.sin(there), -1, 1)))


def stretch_iof(body, heights, angle, phase, own_filter, shared, more=None):
    """The haze's I/F at `heights` km above the body's sphere (`UNIT`) across the limb at `angle`
    degrees round from the sun's direction, seen from afar at `phase` degrees (`scattering.iof`),
    with the haze that `body.haze_of` gives for a filter's own numbers and the shared ones, and with
    `more`, the estimate's numbers, the light scattered more than once."""
    a = np.radians(angle)
    r = body.UNIT + heights
    return scattering.iof(r * np.cos(a), r * np.sin(a), phase, body.haze_of(own_filter, shared), body.STEPS, body.SPREAD, more)


def fit(measured, more, body):
    """The shared numbers, each filter's, and each frame's own, fitted to the stretches, with `more`,
    each filter's numbers for the light scattered more than once, or none. `body` is the body's own
    fit, which gives the filters and the numbers with their first guesses and bounds, the stray
    light's, the heights fitted and their weights, the camera's blur, the haze and the steps along
    a line of sight that `stretch_iof` takes, and how far each frame's edge may stand off the game's
    sphere (`most_shift`), under the names below. A frame may give heights of its own to fit (`fitted`).
    Outside them, a stretch may hold bounds on the model, NaN where there are none: the least I/F
    (`least`), as where the camera saturated, and the most (`most`), as where light the model leaves
    out adds to what it gives."""
    data, weights, kinds, rows_of = [], [], [], []
    for m in measured:
        low, high = m['fitted'] if 'fitted' in m else body.FITTED
        for s in m['stretches']:
            none = np.full(len(s['heights']), np.nan)
            least, most = s.get('least', none), s.get('most', none)
            fitted = (s['heights'] >= low) & (s['heights'] <= high)
            rows = fitted | np.isfinite(least) | np.isfinite(most)
            mean, count = s['mean'][rows], s['count'][rows]
            ok = np.isfinite(mean) & (count >= body.LEAST_PIXELS) & fitted[rows]
            # Each bin's kind: fitted (0), held at least (-1) or at most (1) as bright, or unused.
            kind = np.where(ok, 0, np.where(np.isfinite(least[rows]), -1, np.where(np.isfinite(most[rows]), 1, 0)))
            used = ok | np.isfinite(least[rows]) | np.isfinite(most[rows])
            value = np.where(ok, mean, np.where(kind < 0, least[rows], np.where(kind > 0, most[rows], 0)))
            value = np.nan_to_num(np.where(used, value, 0))
            data.append(value)
            weights.append(np.where(used, 1 / (body.RELATIVE * np.abs(value) + body.ABSOLUTE), 0))
            kinds.append(kind)
            rows_of.append(rows)
    shared_count, filter_count = len(body.SHARED), len(body.OWN_FILTER)
    frame_start = shared_count + filter_count * len(body.FILTERS)

    def split(p):
        shared = p[:shared_count]
        filters = {f: p[shared_count + i * filter_count:shared_count + (i + 1) * filter_count] for i, f in enumerate(body.FILTERS)}
        frames = [p[frame_start + i * len(body.OWN_FRAME):frame_start + (i + 1) * len(body.OWN_FRAME)] for i in range(len(measured))]
        return shared, filters, frames

    def model(m, s, rows, shared, own_filter, own):
        shift, tail, length, offset = own
        # The heights fitted, and a margin round them for the blur.
        step = s['heights'][1] - s['heights'][0]
        sigma = body.BLUR * m['km'] / step
        margin = int(np.ceil(4 * sigma)) + 1
        index = np.nonzero(rows)[0]
        near = slice(max(index[0] - margin, 0), min(index[-1] + margin + 1, len(rows)))
        heights = s['heights'][near]
        iof = stretch_iof(body, heights + shift, s['angle'], s['phase'], own_filter, shared, more[m['filter']])
        iof = ndimage.gaussian_filter1d(iof, sigma, mode='nearest')
        sky = offset + tail * np.exp(-np.clip(heights, 0, None) / length)
        return (iof + sky)[rows[near]]

    def residuals(p):
        shared, filters, frames = split(p)
        out, k = [], 0
        for m, own in zip(measured, frames):
            for s in m['stretches']:
                off = model(m, s, rows_of[k], shared, filters[m['filter']], own) - data[k]
                off = np.where(kinds[k] < 0, np.minimum(off, 0), np.where(kinds[k] > 0, np.maximum(off, 0), off))
                out.append((off * weights[k]).ravel())
                k += 1
        return np.concatenate(out)

    start = list(body.SHARED_FIRST_GUESS) + body.FILTER_FIRST_GUESS * len(body.FILTERS)
    lowest = list(body.SHARED_LOWEST) + body.FILTER_LOWEST * len(body.FILTERS)
    highest = list(body.SHARED_HIGHEST) + body.FILTER_HIGHEST * len(body.FILTERS)
    for m in measured:
        shift = body.most_shift(m)
        shortest = max(body.SHORTEST_TAIL * m['km'], body.SHORTEST_TAIL_KM)
        start += [0.0, body.FRAME_FIRST_GUESS[0], 2 * shortest, body.FRAME_FIRST_GUESS[1]]
        lowest += [-shift, body.FRAME_LOWEST[0], shortest, body.FRAME_LOWEST[1]]
        highest += [shift, body.FRAME_HIGHEST[0], body.LONGEST_TAIL_KM, body.FRAME_HIGHEST[1]]
    # Each stretch's residuals hang on the shared numbers, its filter's and its frame's alone.
    sparsity = sparse.lil_matrix((sum(d.size for d in data), len(start)), dtype=int)
    row, k = 0, 0
    for i, m in enumerate(measured):
        f = body.FILTERS.index(m['filter'])
        for _ in m['stretches']:
            size = data[k].size
            sparsity[row:row + size, :shared_count] = 1
            sparsity[row:row + size, shared_count + f * filter_count:shared_count + (f + 1) * filter_count] = 1
            sparsity[row:row + size, frame_start + i * len(body.OWN_FRAME):frame_start + (i + 1) * len(body.OWN_FRAME)] = 1
            row += size
            k += 1
    result = optimize.least_squares(residuals, start, bounds=(lowest, highest), jac_sparsity=sparsity, x_scale='jac',
                                    max_nfev=body.MOST_EVALUATIONS)
    return split(result.x), result


def describe(measured, fitted, result, body):
    """Prints a fit's numbers (`fit`): its cost, the shared numbers, each filter's and each frame's
    own."""
    shared, filters, owns = fitted
    print(f"fit: cost {result.cost:.3g} after {result.nfev} evaluations")
    print('shared: ' + ', '.join(f'{k} {v:.4g}' for k, v in zip(body.SHARED, shared)))
    for name in body.FILTERS:
        print(f"{name}: " + ', '.join(f'{k} {v:.4g}' for k, v in zip(body.OWN_FILTER, filters[name])))
    for m, own in zip(measured, owns):
        print(f"  {m['name']} ({m['filter']}, {m['phase']:.1f} degrees): " + ', '.join(f'{k} {v:.4g}' for k, v in zip(body.OWN_FRAME, own)))
