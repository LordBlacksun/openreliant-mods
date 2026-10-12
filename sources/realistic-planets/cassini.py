"""Cassini's calibrated frames, shared by Titan's and Saturn's scripts (`titan/compose.py`,
`titan/haze.py`, `saturn/haze.py`): a frame's I/F from its detached PDS3 label, the directions of its
sky in the body's frame, each pixel's geometry, and the disk fitted to the lit limb.
"""
import re

import numpy as np
from scipy import ndimage

import globe

# Cassini's blue, green and red filters' effective wavelengths, nm, as for Saturn's maps (Wang and
# others, 2025).
FILTERS = {'BL1': 463.0, 'GRN': 568.0, 'RED': 647.0}
# The highest I/F a frame's pixel can hold and be trusted: a higher one is a hot pixel or a cosmic ray.
MOST_IF = 5.0
# The limb fit. The first guess at the disk is the pixels brighter than `FIRST_GUESS` of the 99th
# percentile. Rays `RAY_STEP` degrees apart run from the centre over `RAY_REACH` of the radius, in
# `RAY_SAMPLES` steps, and the edge is where a ray's brightness falls to `EDGE` of its median between
# `PLATEAU` of the radius. A ray counts where the sun's cosine at `LIT_AT` of the radius is at least
# `LIT_LIMB`. The fit is repeated `FITS` times from the last disk.
FIRST_GUESS = 0.4
RAY_STEP = 0.5
RAY_REACH = (0.6, 1.4)
RAY_SAMPLES = 401
EDGE = 0.5
PLATEAU = (0.8, 0.9)
LIT_AT = 0.98
LIT_LIMB = 0.3
FITS = 4


def frame(label):
    """A calibrated frame's I/F, from its detached PDS3 label."""
    with open(label, encoding='latin-1') as f:
        text = f.read()
    record = int(re.search(r'^\s*RECORD_BYTES\s*=\s*(\d+)', text, re.M).group(1))
    start = int(re.search(r'\^IMAGE\s*=\s*\("[^"]+",\s*(\d+)\)', text).group(1))
    image = text[re.search(r'OBJECT\s*=\s*IMAGE\s', text).start():]
    lines = int(re.search(r'\bLINES\s*=\s*(\d+)', image).group(1))
    samples = int(re.search(r'\bLINE_SAMPLES\s*=\s*(\d+)', image).group(1))
    data = np.fromfile(label[:-4] + '.IMG', dtype='<f4', count=lines * samples, offset=(start - 1) * record)
    return data.reshape(lines, samples).astype(np.float64)


def trusted(image):
    """A frame's I/F where it can be trusted, and 0 where it can't: missing, below zero, or a hot
    pixel or a cosmic ray."""
    return np.where(np.isfinite(image) & (image > 0) & (image < MOST_IF), image, 0)


def axes(f):
    """A frame's right and up directions on the sky, and the directions toward the observer and the
    sun, in the body's frame: from the frame's sub-spacecraft and sub-solar points, and the clock
    angle of the body's north pole in the frame."""
    observer, sun = globe.unit(f['observer_lat'], f['observer_east_lon']), globe.unit(f['sun_lat'], f['sun_east_lon'])
    north = np.array([0.0, 0.0, 1.0]) - observer[2] * observer
    north /= np.linalg.norm(north)
    across = np.cross(observer, north)
    t = np.radians(f['north_clock_angle'])
    right, up = np.sin(t) * north - np.cos(t) * across, np.cos(t) * north + np.sin(t) * across
    return right, up, observer, sun


def sun_direction(f):
    """The sun's direction in a frame, radians from right toward up."""
    right, up, _, sun = axes(f)
    return np.arctan2(sun @ up, sun @ right)


def geometry(shape, cx, cy, radius, f):
    """Each pixel's latitude and the cosines of its angles of view and light, on a sphere of `radius`
    pixels about (`cx`, `cy`), seen from afar; and where the sphere is."""
    right, up, observer, sun = axes(f)
    lines, samples = np.indices(shape).astype(np.float64)
    x, y = (samples - cx) / radius, (cy - lines) / radius
    disk = x ** 2 + y ** 2 < 1
    mu = np.sqrt(np.clip(1 - x ** 2 - y ** 2, 0, None))
    point = x[..., None] * right + y[..., None] * up + mu[..., None] * observer
    return np.degrees(np.arcsin(np.clip(point[..., 2], -1, 1))), mu, point @ sun, disk


def limb(image, f):
    """The disk's centre and radius, pixels, fitted to the lit limb: along rays from the centre,
    where the brightness falls to `EDGE` of that just inside, and a circle through those points."""
    bright = image > FIRST_GUESS * np.percentile(image, 99)
    cy, cx = np.argwhere(bright).mean(axis=0)
    radius = np.sqrt(bright.sum() / np.pi)
    angles = np.radians(np.arange(0, 360, RAY_STEP))
    for _ in range(FITS):
        _, _, mu0, _ = geometry(image.shape, cx, cy, radius, f)
        r = np.linspace(*RAY_REACH, RAY_SAMPLES) * radius
        xs, ys = cx + np.outer(np.cos(angles), r), cy - np.outer(np.sin(angles), r)
        rays = ndimage.map_coordinates(image, [ys, xs], order=1, mode='constant', cval=0)
        edges = []
        for angle, ray in zip(angles, rays):
            at = (int(round(cy - np.sin(angle) * LIT_AT * radius)), int(round(cx + np.cos(angle) * LIT_AT * radius)))
            if not (0 <= at[0] < image.shape[0] and 0 <= at[1] < image.shape[1]) or mu0[at] < LIT_LIMB:
                continue
            level = EDGE * np.median(ray[(r > PLATEAU[0] * radius) & (r < PLATEAU[1] * radius)])
            above = np.nonzero(ray > level)[0]
            if len(above) == 0 or above[-1] + 1 >= len(r):
                continue
            i = above[-1]
            edge = r[i] + (ray[i] - level) / (ray[i] - ray[i + 1]) * (r[i + 1] - r[i])
            x, y = cx + np.cos(angle) * edge, cy - np.sin(angle) * edge
            if 0 <= x < image.shape[1] - 1 and 0 <= y < image.shape[0] - 1:
                edges.append((x, y))
        cx, cy, radius = globe.circle(np.array(edges))
    return cx, cy, radius
