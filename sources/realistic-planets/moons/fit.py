"""Fits every frame's pointing. The camera's pointing isn't archived for Voyager's frames of these
moons, so it comes from the frames themselves, and from each moon's map:

1. A first guess of the disk's centre (`centre`). The disk's size is known from the moon's distance,
   so each sharp edge in the frame votes for the point that far inward along its gradient: the lit
   limb's votes meet at the centre, while the terminator's scatter.
2. The twist, where north points in the frame: the moon's map, as the frame would see it lit and
   limb darkened, is matched against the frame at twists `COARSE` degrees apart all round, then
   `FINE` apart near the best, and the twist where the two correlate best wins (`match`), found
   between the steps with a parabola.
3. The centre and scale from the sunlit limb, now that it's known which side is lit
   (`voyager.fit_limb`), and the twist again.
4. A set's frames were taken within minutes, so they share a twist: a frame whose twist strays more
   than `STRAY` degrees from the median of its set's is fitted again near that median. A frame that
   still can't be fitted is left out of `fits.json`, and `compose.py` leaves it out of its set.
5. Minnaert's exponent, with the frame's sky taken off (`moons.sky`) and its pixels sorted by the
   map's brightness, each group given its own albedo (`minnaert.fit`), so that bright and dark ground
   don't count as limb darkening.

    python3 fit.py data frames.json fits.json [moon...]

Naming moons fits only those, and keeps the other moons' fits in `fits.json`.
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import minnaert  # noqa: E402
import moons  # noqa: E402
import voyager  # noqa: E402

# The twists matched, degrees: all round, then near the best.
COARSE = 4.0
FINE = 0.5
# The limb darkening of the model the frames are matched against, and the least cosines of the
# light and the view where a pixel counts, both in matching and in fitting Minnaert's law.
MATCH_K = 0.6
LEAST = 0.2
# How far a frame's twist may stray from its set's, degrees.
STRAY = 3.0
# The share of the frame's pixels, its sharpest edges, that vote for the disk's centre, and the blur
# of the votes, pixels.
EDGES = 0.004
VOTE_BLUR = 1.5
# The groups of the map's brightness for Minnaert's law: at most this many, each with at least
# `minnaert.BAND_CELLS` pixels times this.
GROUPS = 20
GROUP_CELLS = 4


def centre(img, radius):
    """The disk's centre, from where the frame's sharpest edges point `radius` pixels inward. Below
    zero, a frame holds only bad data, which would give sharp edges of its own."""
    smooth = ndimage.gaussian_filter(np.clip(img, 0, None), 1.0)
    gy, gx = np.gradient(smooth)
    g = np.hypot(gx, gy)
    ys, xs = np.nonzero(g >= np.quantile(g, 1 - EDGES))
    gx, gy, g = gx[ys, xs], gy[ys, xs], g[ys, xs]
    vx = np.round(xs + radius * gx / g).astype(int)
    vy = np.round(ys + radius * gy / g).astype(int)
    h, w = img.shape
    inside = (vx >= 0) & (vx < w) & (vy >= 0) & (vy < h)
    votes = np.zeros((h, w))
    np.add.at(votes, (vy[inside], vx[inside]), 1.0)
    votes = ndimage.gaussian_filter(votes, VOTE_BLUR)
    y, x = np.unravel_index(np.argmax(votes), votes.shape)
    return float(x), float(y)


def disk_pixels(view, img):
    """Pixels on the disk, inside its limb, about 40 across it or every pixel for a smaller disk."""
    radius = view.body.a / np.linalg.norm(view.observer) / view.pixel * view.scale
    step = max(1.0, radius / 40)
    ys, xs = np.mgrid[0:img.shape[0]:step, 0:img.shape[1]:step]
    inside = (xs - view.cx) ** 2 + (ys - view.cy) ** 2 < (0.97 * radius) ** 2
    return xs[inside], ys[inside]


def seen(view, reduced, xs, ys):
    """Where pixels see the moon, its map's value there, and the cosines of the view and the light."""
    hit, p, mu, mu0 = view.cast(xs, ys)
    lat, lon = moons.lat_lon(p)
    return hit, moons.lookup(reduced, lat, lon), mu, mu0


def match(img, view, reduced, twists, xs, ys):
    """How well the frame correlates with the map seen through `view` at each twist."""
    obs = voyager.sample(img, xs, ys)
    out = []
    for twist in twists:
        v = view.copy()
        v.set(view.cx, view.cy, twist, view.scale)
        hit, a, mu, mu0 = seen(v, reduced, xs, ys)
        ok = hit & (mu > LEAST) & (mu0 > LEAST) & np.isfinite(a) & (obs > 0)
        if ok.sum() < 50:
            out.append(-1.0)
            continue
        model = a[ok] * mu0[ok] ** MATCH_K * mu[ok] ** (MATCH_K - 1)
        out.append(float(np.corrcoef(model, obs[ok])[0, 1]))
    return np.array(out)


def best_twist(img, view, reduced, near=None):
    """The twist where the frame and the map correlate best, and that correlation; None where the
    view sees too little of the moon."""
    xs, ys = disk_pixels(view, img)
    if near is None:
        coarse = np.deg2rad(np.arange(0, 360, COARSE))
        near = coarse[np.argmax(match(img, view, reduced, coarse, xs, ys))]
    fine = near + np.deg2rad(np.arange(-1.5 * COARSE, 1.5 * COARSE + FINE / 2, FINE))
    curve = match(img, view, reduced, fine, xs, ys)
    if curve.max() <= -1:
        return None, None
    twist = voyager.least(-curve, fine)
    return twist % (2 * np.pi), float(curve.max())


def fit_frame(img, view, reduced, mask, near=None):
    """The frame's view, fitted from a first guess of its centre, and the fit's quality: the limb's
    points and their RMS distance, and the correlation with the map; None where it fails."""
    twist, _ = best_twist(img, view, reduced, near)
    if twist is None:
        return None
    view.set(view.cx, view.cy, twist, view.scale)
    view, points, rms = voyager.fit_limb(img, view, mask)
    twist, correlation = best_twist(img, view, reduced, near=twist)
    if twist is None or not np.isfinite(rms):
        return None
    view.set(view.cx, view.cy, twist, view.scale)
    return view, points, rms, correlation


def first_view(img, body, pixel, frame):
    """The frame's view with the disk's centre from the edges' votes, the twist not yet known."""
    radius = body.a / frame['distance_km'] / pixel
    return voyager.View(body, pixel, frame, *centre(img, radius))


def exponent(img, view, reduced):
    """Minnaert's exponent, each group of the map's brightness with an albedo of its own."""
    ys, xs = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(float)
    hit, a, mu, mu0 = seen(view, reduced, xs.ravel(), ys.ravel())
    obs = (img - moons.sky(img, view)).ravel()
    good = hit & (mu > LEAST) & (mu0 > LEAST) & np.isfinite(a) & (obs > 0)
    if good.sum() < 2 * minnaert.BAND_CELLS * GROUP_CELLS:
        return float('nan')
    groups = int(np.clip(good.sum() // (minnaert.BAND_CELLS * GROUP_CELLS), 2, GROUPS))
    edges = np.quantile(a[good], np.linspace(0, 1, groups + 1)[1:-1])
    k, _ = minnaert.fit(obs, np.where(good, mu0, 1), np.where(good, mu, 1), good, np.digitize(np.nan_to_num(a), edges))
    return float(k)


def report(moon, frame, view, points, rms, correlation, k, again=False):
    print(f"{moon:8s} {frame['name']} {frame['filter']:6s} disk {frame['disc_pixels']:5.0f} px: centre ({view.cx:6.1f}, {view.cy:6.1f}) "
          f"twist {np.rad2deg(view.twist):6.1f} scale {view.scale:.4f}, limb {points} points {rms:.2f} px, "
          f"correlation {correlation:.3f}, k {k:.3f}" + (", fitted again near its set's twist" if again else ""), flush=True)


data, listing, out = sys.argv[1:4]
chosen = sys.argv[4:] or list(moons.MOONS)
with open(listing) as f:
    frames = json.load(f)['frames']
fits = {}
if sys.argv[4:] and os.path.exists(out):
    with open(out) as f:
        fits = {name: fit for name, fit in json.load(f).items()
                if any(frame['name'] == name and frame['moon'] not in chosen for frame in frames)}
for moon in chosen:
    reduced = moons.east_at_left(moons.reduce(moons.read_map(data, moon), moons.REDUCED_STEP), moon)
    body = moons.body(moon)
    mine = [f for f in frames if f['moon'] == moon]
    for frame in mine:
        img, pixel = moons.frame(data, frame)
        found = fit_frame(img, first_view(img, body, pixel, frame), reduced, voyager.frame_mask(img))
        if found is None:
            print(f"{moon:8s} {frame['name']} {frame['filter']:6s}: no fit", flush=True)
            continue
        view, points, rms, correlation = found
        k = exponent(img, view, reduced)
        fits[frame['name']] = dict(cx=view.cx, cy=view.cy, twist=view.twist, scale=view.scale, k=k, limb_points=points,
                                   limb_rms=rms, correlation=correlation)
        report(moon, frame, view, points, rms, correlation, k)
    for set_id in sorted({f['set'] for f in mine}):
        members = [f for f in mine if f['set'] == set_id]
        twists = [fits[f['name']]['twist'] for f in members if f['name'] in fits]
        if not twists:
            continue
        # The median on the circle: the twists turned to lie near the first.
        median = float(np.median(np.unwrap(np.array(twists))))
        for frame in members:
            fit = fits.get(frame['name'])
            if fit is not None and abs((fit['twist'] - median + np.pi) % (2 * np.pi) - np.pi) <= np.deg2rad(STRAY):
                continue
            img, pixel = moons.frame(data, frame)
            view = first_view(img, body, pixel, frame)
            found = fit_frame(img, view, reduced, voyager.frame_mask(img), near=median)
            fits.pop(frame['name'], None)
            if found is None or abs((found[0].twist - median + np.pi) % (2 * np.pi) - np.pi) > np.deg2rad(STRAY):
                print(f"{moon:8s} {frame['name']} {frame['filter']:6s}: left out, its twist strays from its set's", flush=True)
                continue
            view, points, rms, correlation = found
            k = exponent(img, view, reduced)
            fits[frame['name']] = dict(cx=view.cx, cy=view.cy, twist=view.twist, scale=view.scale, k=k, limb_points=points,
                                       limb_rms=rms, correlation=correlation)
            report(moon, frame, view, points, rms, correlation, k, again=True)
with open(out, 'w') as f:
    json.dump(fits, f, indent=1)
