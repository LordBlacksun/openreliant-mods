"""Fits every frame's pointing. The cameras' pointing isn't archived for the Neptune encounter, so it
comes from the frames themselves:

1. A first guess of the disk's centre and scale, by matching a lit model disk (`first_guess`).
2. The centre and scale from the sunlit limb, found to a fraction of a pixel (`fit_limb`).
3. The twist, where north points in the frame, one for each day: the frames are mapped at twists
   half a degree apart, and the twist where the bands vary least along each latitude, summed over
   the day's frames, wins (`band_cost`), found between the grid's steps with a parabola through the
   least three. The camera's roll relative to Neptune barely changes over a day, and a single
   frame's estimate is noisy.
4. The limb again with the day's twist, then the limb darkening (`minnaert`).

    python3 fit.py data frames.json fits.json twists.json

`twists.json` keeps each frame's cost curve, over its mean, and each day's twist.
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nepgeo  # noqa: E402
import voyager  # noqa: E402

data, listing, out, twists_out = sys.argv[1:5]
frames = {f['name']: f for f in json.load(open(listing))['frames']}

images, views, ks = {}, {}, {}
for name, frame in frames.items():
    img, _ = voyager.image(f"{data}/{name}_GEOMED.IMG", f"{data}/{name}_GEOMED.LBL")
    images[name] = img
    view, n, rms = voyager.fit_limb(img, voyager.first_guess(img, nepgeo.NEPTUNE, nepgeo.PIXEL, frame), voyager.frame_mask(img))
    views[name], ks[name] = view, voyager.minnaert(img, view)[0]
    print(f"{name} {frame['filter']:6s} limb {n:3d} points, {rms:.2f} px", flush=True)

twists = np.deg2rad(np.arange(-25, 10.01, 0.5))
by_day, curves = defaultdict(list), {}
for name, frame in frames.items():
    img, view = images[name], views[name].copy()
    mask = voyager.frame_mask(img)
    curve = []
    for tw in twists:
        view.set(view.cx, view.cy, tw, view.scale)
        curve.append(nepgeo.band_cost(img, view, ks[name], mask))
    curve = np.array(curve) / np.mean(curve)
    curves[name] = curve
    by_day[frame['time'][:10]].append(curve)


day_twist = {}
for day, day_curves in sorted(by_day.items()):
    day_twist[day] = voyager.least(np.sum(day_curves, axis=0), twists)
    print(f"{day}: twist {np.rad2deg(day_twist[day]):.2f} degrees, from {len(day_curves)} frames", flush=True)
json.dump(dict(twists_deg=np.rad2deg(twists).round(2).tolist(), days={d: np.rad2deg(t) for d, t in day_twist.items()},
               curves={n: c.round(5).tolist() for n, c in curves.items()}), open(twists_out, 'w'), indent=1)

fits = {}
for name, frame in frames.items():
    img, view = images[name], views[name]
    view.set(view.cx, view.cy, day_twist[frame['time'][:10]], view.scale)
    view, n, rms = voyager.fit_limb(img, view, voyager.frame_mask(img))
    k, b = voyager.minnaert(img, view)
    fits[name] = dict(cx=view.cx, cy=view.cy, twist=view.twist, scale=view.scale, k=k, albedo=b, limb_points=n, limb_rms=rms)
    print(f"{name} centre ({view.cx:7.2f}, {view.cy:7.2f}) scale {view.scale:.5f} k {k:.3f} B {b:.3f} limb {rms:.2f} px", flush=True)
json.dump(fits, open(out, 'w'), indent=1)
