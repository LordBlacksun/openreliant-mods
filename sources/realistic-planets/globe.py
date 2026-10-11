"""The area-weighted mean over a body's global map, whose rows run along latitudes, shared by the
bodies' scripts."""
import numpy as np


def area_mean(m, rows, latitudes):
    """The mean of `m` over `rows`, weighted by the area at their planetocentric `latitudes`,
    degrees."""
    weights = np.broadcast_to(np.cos(np.radians(latitudes[rows]))[:, None], m[rows].shape)
    return np.sum(m[rows] * weights) / np.sum(weights)
