"""A body's globe, shared by the bodies' scripts: the direction toward a latitude and longitude, the
area-weighted mean over a global map, whose rows run along latitudes, and the circle of its disk's
edge in a frame."""
import numpy as np


def unit(lat, lon):
    """The unit vector from a body's centre toward planetocentric latitude `lat` and east longitude
    `lon`, degrees: z toward the north pole, x toward 0 degrees east and y toward 90."""
    la, lo = np.radians(lat), np.radians(lon)
    return np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def area_mean(m, rows, latitudes):
    """The mean of `m` over `rows`, weighted by the area at their planetocentric `latitudes`,
    degrees."""
    weights = np.broadcast_to(np.cos(np.radians(latitudes[rows]))[:, None], m[rows].shape)
    return np.sum(m[rows] * weights) / np.sum(weights)


def circle(points):
    """The circle through `points`, (x, y) pixels, that fits them best, as its centre and radius: by
    linear least squares on x^2 + y^2 = 2 cx x + 2 cy y + c."""
    (cx, cy, c), *_ = np.linalg.lstsq(np.c_[2 * points, np.ones(len(points))], (points ** 2).sum(axis=1), rcond=None)
    return cx, cy, np.sqrt(c + cx ** 2 + cy ** 2)
