"""A body's globe, shared by the bodies' scripts: the direction toward a latitude and longitude, and
the area-weighted mean over a global map, whose rows run along latitudes."""
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
