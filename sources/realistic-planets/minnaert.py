"""Minnaert's law, I/F = B mu0^k mu^(k - 1), fitted to a picture or a map of a body, for the bodies'
scripts. Each band of latitude has a brightness B of its own, so that the bands' own brightness, such
as a dark equator where the sun stands highest, doesn't count as limb darkening."""
import numpy as np

# The least cells a band of latitude needs for its brightness to count.
BAND_CELLS = 50


def fit(radiance, mu0, mu, good, bands):
    """The exponent k, fitted where `good`, and each band's brightness B, NaN for a band with fewer
    than `BAND_CELLS` good cells. `bands` numbers each cell's band of latitude from 0."""
    x = np.log(mu0[good] * mu[good])
    y = np.log(radiance[good] * mu[good])
    band = bands[good]
    cells = np.bincount(band)
    x_mean = np.bincount(band, x) / np.maximum(cells, 1)
    y_mean = np.bincount(band, y) / np.maximum(cells, 1)
    kept = cells[band] >= BAND_CELLS
    x, y = (x - x_mean[band])[kept], (y - y_mean[band])[kept]
    k = np.sum(x * y) / np.sum(x ** 2)
    return k, np.where(cells >= BAND_CELLS, np.exp(y_mean - k * x_mean), np.nan)
