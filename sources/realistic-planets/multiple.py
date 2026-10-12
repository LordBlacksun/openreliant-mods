"""The light a body's haze scatters more than once, for the bodies' fits (`titan/haze.py`,
`neptune/haze.py`): a Monte Carlo of all orders of scattering in the haze, and the numbers of the
estimate the shader uses (`scattering.multiple_light`) fitted to it.

- The Monte Carlo follows each line of sight from a camera afar backward into the haze. At each
  scattering it adds the sunlight that reaches the point, Chapman's integral as the model has it,
  scattered toward the path by the phase function. Then the path scatters on, in a direction drawn
  from the phase function, its weight times the albedo, until it leaves the haze, sinks below the
  body's floor, or reaches haze so deep that `DEEP` optical depths lie straight above it, where no
  sunlight reaches. The first order is the model's single scattering, which checks the Monte Carlo;
  the rest is the light scattered more than once.
- A line's first scattering is drawn within the line's optical depth, weighted by the chance of one.
  A path whose weight falls below `LOW_WEIGHT` goes on half the time, at twice the weight.
- The lines: at the phase angles `PHASES`, on the sun's side of the limb, at right angles to it and
  opposite it (`ROUNDS`), at heights above the body's edge that the caller gives.
- The estimate's numbers are fitted by least squares to the logarithm of each line's I/F, first order
  and estimate together against the Monte Carlo's, each lifted by a hundredth of the brightest
  line's at its phase, so that faint lines count in absolute terms.
"""
import numpy as np
from scipy import optimize

import scattering

# The paths: the optical depth straight up where a path ends, the most scatterings it is followed
# through, and the weight below which it may end.
DEEP = 30.0
MOST_ORDERS = 80
LOW_WEIGHT = 0.05
# The steps a path's flight is measured in, km from where it starts, closer near it, out to about
# 16,000 km, past the longest chord through a body's haze.
FLIGHT = np.concatenate([[0.0], 1e-4 * 1.07 ** np.arange(280)])
# The steps along a line of sight, closest where it passes nearest the body.
LINE_STEPS, LINE_SPREAD = 4001, 3.0
# The lines: phase angles, degrees, and angles round the limb from the sun's side, degrees.
PHASES = (30.0, 90.0, 120.0, 141.0, 160.0)
ROUNDS = (0.0, 90.0, 180.0)
# The estimate's numbers' first guesses and bounds: the beam's rate, the glow's amount, its fall
# (km), and the sun's cosine at the middle of its fade and the fade's width.
FIRST_GUESS = [(0.4, 0.5, 100.0, 0.2, 0.15), (0.6, 1.0, 50.0, 0.0, 0.2)]
LOWEST = (0.0, 0.0, 5.0, -1.0, 0.01)
HIGHEST = (3.0, 20.0, 2000.0, 1.0, 1.0)
# How much a faint line's I/F is lifted: a share of the brightest line's at its phase.
FAINT = 0.01
# The estimate's numbers, in the order `scattering.multiple_light` takes them.
NAMES = ['beam', 'glow', 'fall', 'middle', 'width']


def extinction(haze, r):
    """The haze's extinction (`scattering.Haze`), none above its top, where the model ends."""
    return np.where(r > haze.top, 0.0, haze.extinction(r))


def lobe_cosines(g, xi):
    """The cosines of the scattering angle that Henyey and Greenstein's lobe of asymmetry `g` gives for
    the uniform numbers `xi`."""
    g = np.where(np.abs(g) < 1e-6, 1e-6, g)
    return (1 + g * g - ((1 - g * g) / (1 - g + 2 * g * xi)) ** 2) / (2 * g)


def phase_cosines(lobes, n, rng):
    """`n` cosines of the scattering angle drawn from the phase function (`scattering.phase_function`)."""
    first, second, first_share, second_share = lobes
    pick = rng.random(n)
    cos = np.where(pick < first_share, lobe_cosines(first, rng.random(n)), lobe_cosines(second, rng.random(n)))
    rayleigh = pick >= first_share + second_share
    if rayleigh.any():
        # Rayleigh's, drawn from a uniform cosine and kept as often as (1 + cos^2) / 2.
        m = int(rayleigh.sum())
        kept = np.empty(0)
        while kept.size < m:
            u = rng.uniform(-1, 1, 4 * m)
            kept = np.concatenate([kept, u[rng.random(4 * m) < (1 + u * u) / 2]])
        cos[rayleigh] = kept[:m]
    return np.clip(cos, -1, 1)


def turned(directions, cos, rng):
    """`directions` turned by the angles of cosine `cos`, each at a random azimuth."""
    azimuth = rng.uniform(0, 2 * np.pi, len(directions))
    helper = np.where(np.abs(directions[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
    u = np.cross(directions, helper)
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    v = np.cross(directions, u)
    sin = np.sqrt(np.clip(1 - cos * cos, 0, None))
    return cos[:, None] * directions + sin[:, None] * (np.cos(azimuth)[:, None] * u + np.sin(azimuth)[:, None] * v)


def flight(haze, points, directions, target):
    """Where each path, from `points` along `directions`, has crossed `target` optical depths, and
    whether it gets there before it leaves the haze or sinks below the floor."""
    along = points[:, None, :] + FLIGHT[None, :, None] * directions[:, None, :]
    r = np.linalg.norm(along, axis=2)
    s = extinction(haze, r)
    depth = np.concatenate([np.zeros((len(points), 1)), np.cumsum(0.5 * (s[:, 1:] + s[:, :-1]) * np.diff(FLIGHT)[None, :], axis=1)], axis=1)
    reached = depth >= target[:, None]
    first = np.argmax(reached, axis=1)
    ok = reached.any(axis=1)
    sunk = r < haze.floor
    ok &= ~(sunk.any(axis=1) & (np.argmax(sunk, axis=1) <= first))
    i = np.clip(first, 1, len(FLIGHT) - 1)
    rows = np.arange(len(points))
    d0, d1 = depth[rows, i - 1], depth[rows, i]
    distance = FLIGHT[i - 1] + np.clip((target - d0) / np.maximum(d1 - d0, 1e-300), 0, 1) * (FLIGHT[i] - FLIGHT[i - 1])
    return points + distance[:, None] * directions, ok


def line_orders(haze, through, round_, phase, paths, rng):
    """The I/F of the line of sight through the sky point `through` km from the body's centre,
    `round_` degrees round the limb from the sun's side, at `phase` degrees: its first order and the
    rest, from `paths` paths."""
    a, w = np.radians(phase), np.radians(round_)
    sun = np.array([np.sin(a), 0.0, np.cos(a)])
    chord = np.sqrt(haze.top ** 2 - through ** 2)
    # The line from the camera's side down, its optical depth on a fine grid, ending at the floor.
    u = np.linspace(-1, 1, LINE_STEPS)
    z = (chord * np.sinh(LINE_SPREAD * u) / np.sinh(LINE_SPREAD))[::-1]
    if through < haze.floor:
        z = z[z >= np.sqrt(haze.floor ** 2 - through ** 2)]
    s = extinction(haze, np.sqrt(through ** 2 + z ** 2))
    depth = np.concatenate([[0.0], np.cumsum(0.5 * (s[1:] + s[:-1]) * np.abs(np.diff(z)))])
    chance = 1 - np.exp(-depth[-1])
    zs = np.interp(-np.log(1 - rng.random(paths) * chance), depth, z)
    points = np.stack([np.full(paths, through * np.cos(w)), np.full(paths, through * np.sin(w)), zs], axis=1)
    directions = np.tile([0.0, 0.0, -1.0], (paths, 1))
    weight = np.full(paths, chance)
    alive = np.ones(paths, dtype=bool)
    first = rest = 0.0
    for order in range(MOST_ORDERS):
        if not alive.any():
            break
        idx = np.nonzero(alive)[0]
        r = np.linalg.norm(points[idx], axis=1)
        sunlight = np.exp(-haze.sun_depth(r, (points[idx] @ sun) / r))
        light = np.sum(weight[idx] * haze.albedo * scattering.phase_function(directions[idx] @ sun, *haze.lobes) / 4 * sunlight)
        if order == 0:
            first = light
        else:
            rest += light
        weight[idx] *= haze.albedo
        directions[idx] = turned(directions[idx], phase_cosines(haze.lobes, len(idx), rng), rng)
        points[idx], ok = flight(haze, points[idx], directions[idx], -np.log(1 - rng.random(len(idx))))
        deep = extinction(haze, np.linalg.norm(points[idx], axis=1)) * haze.scale > DEEP
        alive[idx] = ok & ~deep
        low = alive & (weight < LOW_WEIGHT)
        ended = low & (rng.random(paths) < 0.5)
        alive &= ~ended
        weight = np.where(low & ~ended, 2 * weight, weight)
    return first / paths, rest / paths


def monte_carlo(haze, heights, unit, paths, seed):
    """The Monte Carlo's lines: at each phase in `PHASES` and each angle round in `ROUNDS`, at
    `heights` km above the radius `unit`, each with its first order and the rest."""
    rng = np.random.default_rng(seed)
    return [dict(phase=phase, round=round_, height=h, first=first, rest=rest)
            for phase in PHASES for round_ in ROUNDS for h in heights
            for first, rest in [line_orders(haze, unit + h, round_, phase, paths, rng)]]


def fit(haze, lines, unit, steps, spread):
    """The estimate's numbers (`scattering.multiple_light`) that best follow the Monte Carlo's lines,
    and how far each line's I/F, with them, is from the Monte Carlo's."""
    brightest = {}
    for line in lines:
        brightest[line['phase']] = max(brightest.get(line['phase'], 0.0), line['first'] + line['rest'])
    used = [line for line in lines if brightest[line['phase']] > 0]
    prepared = []
    for line in used:
        w = np.radians(line['round'])
        b = unit + line['height']
        along = scattering.sky_lines(np.array([b * np.cos(w)]), np.array([b * np.sin(w)]), line['phase'], haze, steps, spread)
        prepared.append((along, -np.cos(np.radians(line['phase'])), FAINT * brightest[line['phase']]))

    def residuals(numbers):
        out = []
        for line, (along, cos_theta, lift) in zip(used, prepared):
            more = scattering.multiple_light(along, haze, cos_theta, numbers)[0]
            out.append(np.log((line['first'] + more + lift) / (line['first'] + line['rest'] + lift)))
        return np.array(out)

    best = min((optimize.least_squares(residuals, start, bounds=(LOWEST, HIGHEST)) for start in FIRST_GUESS), key=lambda f: f.cost)
    return tuple(best.x), np.expm1(best.fun)


def estimate(haze, heights, unit, paths, seed, steps, spread):
    """The estimate's numbers for the light `haze` scatters more than once: the Monte Carlo's lines
    at `heights` km above the radius `unit`, and the estimate fitted to them (`fit`)."""
    return fit(haze, monte_carlo(haze, heights, unit, paths, seed), unit, steps, spread)


def describe(numbers, off):
    """The estimate's numbers, and how far the Monte Carlo's lines are from it, for a fit's printout."""
    return (', '.join(f'{name} {value:.4g}' for name, value in zip(NAMES, numbers))
            + f"; the Monte Carlo's lines within {np.sqrt(np.mean(np.log1p(off) ** 2)):.1%} rms, at worst {off[np.argmax(np.abs(off))]:+.0%}")
