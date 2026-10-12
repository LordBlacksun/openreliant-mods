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
geometry is worked out from the camera's place (`edges.sight`), and a pixel's size at the edge from the
camera's distance to the edge (`km_per_pixel`). The frames at 136 degrees, from 32 radii, are close
to a view from afar.

The measurements:

- Each frame's limb is a circle fitted to its half-maximum edge: where, along each ray from the
  circle's centre, the brightness falls to half way between the peak just inside it and the sky
  just outside. The first guess is a circle through the bright crescent's peak, just inside the
  limb (`edges.edge_guess`).
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
  with the sun as high above it (`edges.from_afar`).

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
from scipy import ndimage, optimize

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import edges  # noqa: E402
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


def crescent(depth, angle, phase, distance, k):
    """Minnaert's law's factor, mu0^k mu^(k-1), with exponent `k`, at `depth` km inside the edge of
    a stretch `angle` degrees round from the sun's direction, seen by a camera `distance` km from the
    middle at `phase` degrees, the view's cosine held at `LEAST_MU`."""
    point, line, sun = edges.sight(UNIT, distance, phase, angle, depth)
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


def measure(data, f):
    """A frame's limb, in `SEGMENTS` stretches: each one's I/F averaged in bins of height above the
    edge, with the pixels in each bin, its angle round from the sun's direction, and its edge as a
    view from afar shows it (`edges.from_afar`)."""
    image = frame(data, f)
    km = km_per_pixel(f, data)
    guess = edges.edge_guess(image, UNIT / km)
    (cx, cy, r), points, angles, rms = edges.edge_fit(image, guess)
    lines, samples = np.indices(image.shape).astype(np.float64)
    x, y = samples - cx, cy - lines
    height = edges.above(x, y, r) * km
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
        heights, mean, count = edges.binned(image, height, along & (height >= bins[0]) & (height < bins[-1]), bins)
        depth, light, seen = edges.binned(image, height, along & (height >= inward[0]) & (height < inward[-1]), inward)
        used = (seen >= LEAST_PIXELS) & np.isfinite(light)
        angle = crescent_angle(-depth[used], light[used], f['phase'], f['distance_km'], EXPONENT[f['filter']])
        phase, afar = edges.from_afar(UNIT, f['distance_km'], f['phase'], angle)
        stretches.append(dict(heights=heights, mean=mean, count=count, angle=afar, phase=phase, round=angle))
    print(f"{f['name']} ({f['filter']}, {f['phase']:.1f} degrees, {km:.2f} km a pixel): edge rms {rms:.2f} px over "
          f"{len(points)} points; stretches " + ', '.join(f"{s['round']:.1f}" for s in stretches) + " degrees round from the sun's "
          "direction, at " + ', '.join(f"{s['phase']:.1f}" for s in stretches) + " degrees of phase")
    return dict(name=f['name'], filter=f['filter'], phase=f['phase'], km=km, stretches=stretches)


def haze_of(own_filter, shared):
    """A filter's haze as the model and the Monte Carlo take it (`scattering.Haze`): one lobe and
    Rayleigh's."""
    log_extinction, scale, albedo = own_filter
    lobe, share = shared
    return scattering.Haze(UNIT + REFERENCE, log_extinction, scale, albedo, (lobe, 0.0, share, 0.0), UNIT + TOP, UNIT - FLOOR)


def most_shift(m):
    """How far a frame's edge may stand off the game's sphere, km: within a hair of it past
    `SPHERE_PHASE` degrees, as the bounds must stand apart, and up to `MOST_SHIFT` before."""
    return 1e-6 if m['phase'] > SPHERE_PHASE else MOST_SHIFT


def estimate(own_filter, shared, seed):
    """The estimate's numbers for the light a filter's fitted haze scatters more than once, fitted
    to a Monte Carlo of it, and how far the Monte Carlo's lines are from them."""
    return multiple.estimate(haze_of(own_filter, shared), MULTIPLE_HEIGHTS, UNIT, MULTIPLE_PATHS, seed, STEPS, SPREAD)


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
            fitted, result = edges.fit(measured, more, sys.modules[__name__])
            shared, filters, owns = fitted
            if fit_round == FIT_ROUNDS - 1:
                break
            estimates = pool.starmap(estimate, [(filters[name], shared, seed) for seed, name in enumerate(FILTERS)])
            more = {name: numbers for name, (numbers, off) in zip(FILTERS, estimates)}
            for name, (numbers, off) in zip(FILTERS, estimates):
                print(f"round {fit_round + 1}, {name}: {multiple.describe(numbers, off)}")
    edges.describe(measured, fitted, result, sys.modules[__name__])
    colour_filters = ['Blue', 'Green', 'Orange']
    numbers = np.array([filters[name] for name in colour_filters]).T
    lobe, share = shared
    # One lobe and Rayleigh's, and no detached layer, whose extinction is 0.
    print('for neptune.glsl:')
    print(scattering.constructor(
        'neptuneHaze', UNIT, UNIT + REFERENCE, UNIT + TOP, np.exp(numbers[0]), numbers[1], [0.0] * 3, [UNIT] * 3, [1.0] * 3,
        -np.cos(np.radians(texture_phase)), numbers[2], [lobe] * 3, [0.0] * 3, [share] * 3, [0.0] * 3,
        [more[name] for name in colour_filters], [colours[name] for name in colour_filters], BLOOM))
