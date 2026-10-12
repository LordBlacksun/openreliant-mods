"""Voyager's narrow-angle frames as the PDS Ring-Moon Systems Node's GEOMED products hold them, shared
by the bodies' scripts: reading a frame, a body's geometry as the frame sees it, and the frame's
pointing fitted to the body's sunlit limb.

Body-fixed frame: z toward the north pole, x toward 0 degrees east longitude, y toward 90 east. Map
latitudes are planetographic, directions from the centre planetocentric; longitudes are east.
"""
import re

import numpy as np
from scipy import ndimage, optimize

import globe


def label(path):
    """A PDS3 label's fields, the first value of each key."""
    with open(path, encoding='latin-1') as f:
        text = f.read()
    fields = {}
    for key, value in re.findall(r'^\s*([A-Z_^]+)\s*=\s*(.+?)\s*$', text, re.M):
        fields.setdefault(key, value.strip().strip('"'))
    return fields


def image(path_img, path_lbl):
    """A GEOMED image as I/F, and its label's fields. The image holds a VICAR header record, then 1000
    by 1000 16-bit integers that are I/F times the label's REFLECTANCE_SCALING_FACTOR."""
    fields = label(path_lbl)
    record = int(fields['RECORD_BYTES'])
    lines, samples = int(fields['LINES']), int(fields['LINE_SAMPLES'])
    start = int(re.search(r'\(".*?",\s*(\d+)\)', fields['^IMAGE']).group(1)) - 1
    raw = np.fromfile(path_img, dtype='<i2', count=lines * samples, offset=start * record)
    scale = float(fields.get('REFLECTANCE_SCALING_FACTOR', '1').split()[0])
    return raw.reshape(lines, samples).astype(np.float64) * scale, fields


def pixel(fields):
    """A GEOMED pixel's size, radians, from its label."""
    return np.deg2rad(float(fields['HORIZONTAL_PIXEL_FOV'].split()[0]))


class Body:
    """A body as an ellipsoid of revolution: its equatorial radius `a` and polar radius `c`, km."""

    def __init__(self, a, c):
        self.a, self.c = a, c
        self.e2 = 1 - (c / a) ** 2

    def surface(self, lat_g, lon):
        """Points on the body at planetographic latitudes and east longitudes, degrees."""
        la, lo = np.deg2rad(lat_g), np.deg2rad(lon)
        n = self.a / np.sqrt(1 - self.e2 * np.sin(la) ** 2)
        return np.stack([n * np.cos(la) * np.cos(lo), n * np.cos(la) * np.sin(lo), n * (1 - self.e2) * np.sin(la)], axis=-1)

    def normal(self, p):
        g = p / np.array([self.a * self.a, self.a * self.a, self.c * self.c])
        return g / np.linalg.norm(g, axis=-1, keepdims=True)


class View:
    """A frame's geometry: the body, the size of a pixel in radians, the observer and the sun from
    OPUS, and the pointing fitted to the image, as the disk's centre in pixels, the twist of north
    in radians and a scale near 1."""

    def __init__(self, body, pixel, frame, cx=500.0, cy=500.0, twist=0.0, scale=1.0):
        self.body, self.pixel = body, pixel
        self.observer = frame['distance_km'] * globe.unit(frame['observer_lat'], frame['observer_east_lon'])
        self.sun = globe.unit(frame['sun_lat'], frame['sun_east_lon'])
        f = -self.observer / np.linalg.norm(self.observer)
        z = np.array([0.0, 0.0, 1.0])
        n = z - z.dot(f) * f
        n /= np.linalg.norm(n)
        self.forward, self.north, self.right = f, n, np.cross(f, n)
        self.set(cx, cy, twist, scale)

    def set(self, cx, cy, twist, scale):
        self.cx, self.cy, self.twist, self.scale = cx, cy, twist, scale

    def copy(self):
        v = View.__new__(View)
        v.__dict__.update(self.__dict__)
        return v

    def project(self, p):
        """Pixel x and y of body-fixed points p (..., 3)."""
        d = p - self.observer
        dz = d @ self.forward
        u, w = (d @ self.right) / dz, (d @ self.north) / dz
        ct, st, k = np.cos(self.twist), np.sin(self.twist), self.scale / self.pixel
        return self.cx + k * (u * ct - w * st), self.cy - k * (u * st + w * ct)

    def angles(self, p):
        """Cosines of the emission and incidence angles at body-fixed surface points p."""
        nrm = self.body.normal(p)
        to_observer = self.observer - p
        to_observer /= np.linalg.norm(to_observer, axis=-1, keepdims=True)
        return np.sum(nrm * to_observer, axis=-1), nrm @ self.sun

    def cast(self, x, y):
        """For pixels x, y: whether the ray hits the body, where, and the cosines there."""
        k = self.pixel / self.scale
        a, b = (x - self.cx) * k, -(y - self.cy) * k
        ct, st = np.cos(self.twist), np.sin(self.twist)
        u, w = a * ct + b * st, -a * st + b * ct
        d = self.forward + u[..., None] * self.right + w[..., None] * self.north
        s = np.array([1.0, 1.0, self.body.a / self.body.c])
        o, dd = self.observer * s, d * s
        qa = np.sum(dd * dd, axis=-1)
        qb = 2 * dd @ o
        qc = o @ o - self.body.a * self.body.a
        disc = qb * qb - 4 * qa * qc
        hit = disc > 0
        t = (-qb - np.sqrt(np.where(hit, disc, 0))) / (2 * qa)
        p = self.observer + t[..., None] * d
        mu, mu0 = self.angles(p)
        return hit, p, mu, mu0


def sample(img, x, y):
    return ndimage.map_coordinates(img, [y, x], order=1, mode='constant', cval=np.nan)


def model(view, x, y, k, albedo):
    """A lit disk with Minnaert's limb darkening, I/F = albedo mu0^k mu^(k-1), black elsewhere."""
    hit, _, mu, mu0 = view.cast(x, y)
    lit = hit & (mu0 > 0) & (mu > 0)
    m0, m = np.clip(mu0, 1e-6, 1), np.clip(mu, 1e-6, 1)
    return np.where(lit, albedo * m0 ** k * m ** (k - 1), 0.0)


def minnaert(img, view, least=0.25):
    """The Minnaert exponent k and albedo B of a frame: log(I mu) = log(B) + k log(mu mu0)."""
    ys, xs = np.mgrid[8:992:2, 8:992:2].astype(float)
    hit, _, mu, mu0 = view.cast(xs, ys)
    obs = img[8:992:2, 8:992:2]
    ok = hit & (mu > least) & (mu0 > least) & (obs > 0.01)
    k, logb = np.polyfit(np.log(mu[ok] * mu0[ok]), np.log(obs[ok] * mu[ok]), 1)
    return float(k), float(np.exp(logb))


def frame_mask(img, erode=6):
    """Where the frame holds data: GEOMED fills what lies outside the original frame with exact
    zeros, which the sky's noise rarely gives; a few pixels in from there."""
    m = ndimage.binary_closing(img != 0, iterations=3)
    return ndimage.binary_erosion(m, iterations=erode).astype(float)


def albedo_grid(img, view, k, lats, lons, least=0.3, mask=None, shift=None):
    """The frame's albedo, I/F over mu0^k mu^(k-1), on a latitude-longitude grid, NaN where the
    frame doesn't see it well; and mu and mu0 there. `shift` moves each latitude's longitudes east
    by that many degrees, to bring the clouds to another moment."""
    la, lo = np.meshgrid(lats, lons, indexing='ij')
    if shift is not None:
        lo = lo - shift[:, None]
    p = view.body.surface(la, lo)
    mu, mu0 = view.angles(p)
    x, y = view.project(p)
    h, w = img.shape
    if mask is None:
        mask = frame_mask(img)
    ok = (mu > least) & (mu0 > least) & (x > 1) & (x < w - 2) & (y > 1) & (y < h - 2)
    ok &= sample(mask, np.where(ok, x, 0), np.where(ok, y, 0)) > 0.999
    vals = sample(img, np.where(ok, x, 0), np.where(ok, y, 0))
    corr = np.clip(mu0, 1e-3, 1) ** k * np.clip(mu, 1e-3, 1) ** (k - 1)
    return np.where(ok, vals / corr, np.nan), mu, mu0


def smooth(a, sigma_deg, step):
    """A Gaussian blur of a latitude-longitude map that skips gaps and wraps round in longitude."""
    s = sigma_deg / step
    num = ndimage.gaussian_filter(np.nan_to_num(a), s, mode=('nearest', 'wrap'))
    den = ndimage.gaussian_filter(np.isfinite(a).astype(float), s, mode=('nearest', 'wrap'))
    return np.where(den > 0.2, num / np.maximum(den, 1e-9), np.nan)


def least(values, at):
    """Where a curve sampled at evenly spaced points `at` is least, between the samples, from a
    parabola through the lowest three."""
    i = int(np.clip(np.argmin(values), 1, len(values) - 2))
    a, b, c = values[i - 1:i + 2]
    return float(at[i] + 0.5 * (a - c) / (a - 2 * b + c) * (at[1] - at[0]))


def limb_radius(view, angles):
    """The model limb's distance from the disk's centre, in pixels, along image directions (radians
    from +x toward +y)."""
    lo = np.zeros_like(angles)
    hi = np.full_like(angles, 2.0 * view.body.a / np.linalg.norm(view.observer) / view.pixel * view.scale)
    for _ in range(40):
        mid = (lo + hi) / 2
        hit, _, _, _ = view.cast(view.cx + mid * np.cos(angles), view.cy + mid * np.sin(angles))
        lo, hi = np.where(hit, mid, lo), np.where(hit, hi, mid)
    return (lo + hi) / 2


def limb_points(img, view, mask, step_deg=1.0, least_mu0=0.15):
    """Where the sunlit limb is: along each radial line, the radius at which the brightness falls to
    half way between the disk just inside it and the sky, to a fraction of a pixel."""
    angles = np.deg2rad(np.arange(0, 360, step_deg))
    found = []
    for ang, rm in zip(angles, limb_radius(view, angles)):
        # The dark limb near the terminator is skipped, judged a little inside the limb, where the
        # sun stands low even on the lit side; so are the frame's edges.
        hit, _, _, mu0 = view.cast(np.array([view.cx + 0.97 * rm * np.cos(ang)]), np.array([view.cy + 0.97 * rm * np.sin(ang)]))
        if not hit[0] or mu0[0] < least_mu0:
            continue
        r = np.arange(0.85 * rm, 1.12 * rm, 0.25)
        xs, ys = view.cx + r * np.cos(ang), view.cy + r * np.sin(ang)
        if np.any(sample(mask, xs, ys) < 0.999):
            continue
        prof = sample(img, xs, ys)
        inside = np.median(prof[(r > 0.90 * rm) & (r < 0.96 * rm)])
        sky = np.median(prof[r > 1.06 * rm])
        half = sky + 0.5 * (inside - sky)
        below = np.nonzero((prof[:-1] >= half) & (prof[1:] < half) & (r[:-1] > 0.95 * rm))[0]
        if below.size == 0 or inside < 0.05:
            continue
        i = below[0]
        t = (prof[i] - half) / (prof[i] - prof[i + 1])
        found.append((ang, r[i] + t * (r[i + 1] - r[i])))
    return np.array(found)


def fit_limb(img, view, mask, rounds=3):
    """Refits the centre and scale, the twist kept, so that the model limb runs through the measured
    limb points. Returns the view, the number of points and their RMS distance in pixels."""
    rms = np.nan
    pts = np.empty((0, 2))
    for _ in range(rounds):
        pts = limb_points(img, view, mask)
        if len(pts) < 30:
            return view, len(pts), np.nan
        px = view.cx + pts[:, 1] * np.cos(pts[:, 0])
        py = view.cy + pts[:, 1] * np.sin(pts[:, 0])

        def residual(p):
            v = view.copy()
            v.set(p[0], p[1], view.twist, p[2])
            return np.hypot(px - p[0], py - p[1]) - limb_radius(v, np.arctan2(py - p[1], px - p[0]))

        sol = optimize.least_squares(residual, [view.cx, view.cy, view.scale], x_scale=[0.5, 0.5, 0.0005], loss='soft_l1', f_scale=1.0)
        view.set(sol.x[0], sol.x[1], view.twist, sol.x[2])
        rms = float(np.sqrt(np.mean(sol.fun ** 2)))
    return view, len(pts), rms


def first_guess(img, body, pixel, frame, twists=np.deg2rad(np.arange(-30, 21, 5)), k=0.75):
    """A starting point for the limb fit: the centre and scale where a lit model disk matches the
    reduced image best, over a coarse set of twists. Its centre is biased by where the model's
    limb darkening fails, which the limb fit then corrects."""
    ys, xs = np.mgrid[0:1000:4, 0:1000:4].astype(float)
    obs = img[::4, ::4]
    valid = obs > -0.05
    bright = obs > 0.5 * np.percentile(obs[obs > 0.05], 50)
    cy0, cx0 = np.mean(ys[bright]), np.mean(xs[bright])
    albedo = np.percentile(obs[bright], 90)
    best = None
    for tw in twists:
        def residual(p):
            return (model(View(body, pixel, frame, p[0], p[1], tw, p[2]), xs, ys, k, albedo) - obs)[valid]
        sol = optimize.least_squares(residual, [cx0, cy0, 1.0], x_scale=[10, 10, 0.01], max_nfev=60)
        if best is None or sol.cost < best[0]:
            best = (sol.cost, tw, sol.x)
    _, tw, (cx, cy, scale) = best
    return View(body, pixel, frame, cx, cy, tw, scale)
