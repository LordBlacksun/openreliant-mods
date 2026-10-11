"""Mosaics frames into a latitude-longitude map of albedo, brought to one moment.

    python3 mosaic.py data frames.json fits.json pattern.npy <luminance|Orange|Green|Blue> <epoch>
        <step degrees> <out.npz>

Luminance takes the frames whose role is luminance and divides each by its own fitted albedo, so
that clear and green frames agree; a filter takes the colour frames through it and keeps their
albedo, as the filters' ratios are the colour. For each frame:

- single bad pixels give way to their neighbours' median, and the camera's fixed blemishes are
  divided out (`blemishes.py`);
- the clouds are moved to the epoch with Neptune's zonal winds (`nepgeo.drift`);
- the limb darkening is divided out with the frame's Minnaert exponent;
- each map cell is weighted by how squarely it was seen and lit, by the frame's resolution and by
  its distance from the frame's edge, raised to a power so that the best view of each spot
  outweighs the others without hard seams.

Then a photometric self-calibration: where frames overlap, the same cloud is seen at different
angles, so a gain for each frame and a smooth error in the viewing and lighting angles shared by
every frame are fitted to the overlaps' brightness ratios, robustly, and divided out.
"""
import json
import os
import sys
from datetime import datetime

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import nepgeo  # noqa: E402
import voyager  # noqa: E402

data, listing, fits_path, pattern_path, which, epoch, step, out = sys.argv[1:9]
frames = json.load(open(listing))['frames']
fits = json.load(open(fits_path))
epoch = datetime.fromisoformat(epoch)
step = float(step)
if which == 'luminance':
    names, relative = [f['name'] for f in frames if f['role'] == 'luminance'], True
else:
    names, relative = [f['name'] for f in frames if f['role'] == 'colour' and f['filter'] == which], False
frames = {f['name']: f for f in frames}

yy, xx = np.mgrid[0:1000, 0:1000]
blemished = np.zeros((1000, 1000), bool)
for bx, by in nepgeo.BLEMISHES:
    blemished |= (xx - bx) ** 2 + (yy - by) ** 2 <= nepgeo.BLEMISH_RADIUS ** 2
pattern = np.where(blemished, np.load(pattern_path), 0.0)

lats = np.arange(-90 + step / 2, 90, step)
lons = np.arange(step / 2, 360, step)
POWER = 3.0
albedos, weights, mus, mu0s = [], [], [], []
for name in names:
    frame, f = frames[name], fits[name]
    img, _ = voyager.image(f"{data}/{name}_GEOMED.IMG", f"{data}/{name}_GEOMED.LBL")
    med = ndimage.median_filter(img, size=3)
    img = np.where(np.abs(img - med) > 0.02, med, img) / (1.0 + pattern)
    view = nepgeo.view(frame, f['cx'], f['cy'], f['twist'], f['scale'])
    mask = voyager.frame_mask(img)
    inside = ndimage.distance_transform_edt(mask > 0)
    seconds = (epoch - datetime.fromisoformat(frame['time'][:19])).total_seconds()
    shift = nepgeo.drift(lats, seconds)
    a, mu, mu0 = voyager.albedo_grid(img, view, f['k'], lats, lons, least=0.25, mask=mask, shift=shift)
    if relative:
        a = a / f['albedo']
    la, lo = np.meshgrid(lats, lons, indexing='ij')
    x, y = view.project(nepgeo.NEPTUNE.surface(la, lo - shift[:, None]))
    edge = np.clip(voyager.sample(inside, x, y) / 40.0, 0, 1)
    w = np.where(np.isfinite(a), (np.clip(mu, 0, 1) * np.clip(mu0, 0, 1)) ** 2 * np.nan_to_num(edge) / frame['resolution_km'] ** 2, 0.0)
    albedos.append(a.astype(np.float32))
    weights.append(w ** POWER)
    mus.append(mu.astype(np.float32))
    mu0s.append(mu0.astype(np.float32))
    print(f"{name} {frame['filter']:6s} {frame['time'][:16]}  moved {nepgeo.drift(np.array([0.0]), seconds)[0]:+6.1f} degrees at the equator", flush=True)


def basis(mu, mu0):
    u, v = 1 - mu, 1 - mu0
    return np.stack([u, u * u, v, v * v, u * v], axis=-1)


n, nb = len(names), 5
rng = np.random.default_rng(1)
rows, rhs = [], []
for i in range(n):
    for j in range(i + 1, n):
        ok = (np.isfinite(albedos[i]) & np.isfinite(albedos[j]) & (mus[i] > 0.3) & (mus[j] > 0.3) & (mu0s[i] > 0.3) & (mu0s[j] > 0.3))
        idx = np.flatnonzero(ok)
        if idx.size < 2000:
            continue
        idx = rng.choice(idx, min(idx.size, 20000), replace=False)
        X = np.zeros((idx.size, n + nb))
        X[:, i], X[:, j] = 1.0, -1.0
        X[:, n:] = basis(mus[i].ravel()[idx], mu0s[i].ravel()[idx]) - basis(mus[j].ravel()[idx], mu0s[j].ravel()[idx])
        rows.append(X)
        rhs.append(np.log(albedos[i].ravel()[idx]) - np.log(albedos[j].ravel()[idx]))
X = np.vstack(rows + [np.concatenate([np.ones(n), np.zeros(nb)])[None] * 100.0])
y = np.concatenate(rhs + [np.zeros(1)])
keep = np.ones(y.size, bool)
for _ in range(4):
    sol = np.linalg.lstsq(X[keep], y[keep], rcond=None)[0]
    r = y - X @ sol
    spread = 1.4826 * np.median(np.abs(r[keep][:-1]))
    keep = np.abs(r) < 4 * spread
    keep[-1] = True
log_gain, coeff = sol[:n], sol[n:]
print(f"self-calibration: {y.size - 1} sample pairs, {np.mean(~keep) * 100:.1f}% left out, scatter {spread:.4f}")
shared = np.concatenate([np.exp(basis(mu[w > 0].astype(np.float64), mu0[w > 0].astype(np.float64)) @ coeff)
                         for w, mu, mu0 in zip(weights, mus, mu0s)])
print(f"frames' gains {np.exp(log_gain.min()):.3f} to {np.exp(log_gain.max()):.3f}; shared correction "
      f"{np.percentile(shared, 1):.3f} to {np.percentile(shared, 99):.3f} over the cells used (1st to 99th percentile)")

# The mosaic with and without the calibration, the second for comparison.
total = np.zeros((lats.size, lons.size))
plain = np.zeros_like(total)
weight = np.zeros_like(total)
for a, w, lg, mu, mu0 in zip(albedos, weights, log_gain, mus, mu0s):
    correction = np.exp(lg + basis(mu.astype(np.float64), mu0.astype(np.float64)) @ coeff)
    total += np.nan_to_num(a.astype(np.float64) / correction) * w
    plain += np.nan_to_num(a.astype(np.float64)) * w
    weight += w
albedo = np.where(weight > 0, total / np.maximum(weight, 1e-300), np.nan)
uncalibrated = np.where(weight > 0, plain / np.maximum(weight, 1e-300), np.nan)
np.savez_compressed(out, albedo=albedo, uncalibrated=uncalibrated, lats=lats, lons=lons)
print(f"{out}: {albedo.shape}, {np.mean(np.isfinite(albedo)) * 100:.1f}% covered")
