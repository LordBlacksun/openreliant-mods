"""Venus's photometry, shared by `compose.py` and `limb.py`: its spectrum in the visible, at the phase
angle the texture takes its colour at, and Minnaert's law fitted to a map or a frame."""
import numpy as np

# Mallama, Krobusek and Pavlov (2017): Venus's geometric albedo in the Sloan bands and the Johnson B
# and V bands (Table 7), at each band's effective wavelength, nm (Tables 1 and 2), and the coefficients
# of its phase curve, magnitudes per degree to the first to the fourth power (Tables A-2.2 and A-2.3;
# the u' band's are the B band's, as the paper takes them).
BANDS = {
    "u'": (355.0, 0.326, (5.650e-3, 2.438e-4, -2.001e-6, 6.952e-9)),
    'B': (436.0, 0.658, (5.650e-3, 2.438e-4, -2.001e-6, 6.952e-9)),
    "g'": (469.0, 0.664, (3.909e-3, 2.763e-4, -2.213e-6, 7.468e-9)),
    'V': (549.0, 0.689, (-1.044e-3, 3.687e-4, -2.814e-6, 8.938e-9)),
    "r'": (616.0, 0.712, (2.014e-3, 2.706e-4, -1.772e-6, 5.516e-9)),
    "i'": (748.0, 0.708, (2.554e-3, 2.219e-4, -1.080e-6, 2.795e-9)),
}
# The phase angle whose colour the texture takes, degrees, and the Sun's B-V (Table 6).
PHASE = 45.0
SUN_B_V = 0.65
# The least cells a band of latitude needs for its brightness to count in fitting Minnaert's law.
BAND_CELLS = 50


def fainter(coefficients):
    """How many magnitudes fainter a band of Venus is at `PHASE` degrees than at full phase."""
    return sum(c * PHASE ** (n + 1) for n, c in enumerate(coefficients))


def spectrum():
    """Each band's effective wavelength, nm, and Venus's albedo in it at `PHASE` degrees, with the V
    band at its geometric albedo."""
    v = BANDS['V'][2]
    points, values = zip(*[(wavelength, albedo * 10 ** (-0.4 * (fainter(phase) - fainter(v))))
                           for wavelength, albedo, phase in BANDS.values()])
    return np.array(points), np.array(values)


def b_minus_v(values):
    """The B-V colour of albedos in the order of `BANDS`."""
    names = list(BANDS)
    return SUN_B_V - 2.5 * np.log10(values[names.index('B')] / values[names.index('V')])


def channels(lam, albedo, matrix):
    """Each sRGB channel's wavelength for a spectrum, nm: the mean of the wavelengths it takes in, weighted
    by how much of each it takes in. `matrix` is `truecolour.matrix(lam)`."""
    weights = np.clip(matrix, 0, None) * albedo[:, None]
    return (lam[:, None] * weights).sum(axis=0) / weights.sum(axis=0)


def minnaert(radiance, mu0, mu, good, bands):
    """Minnaert's exponent k, by which I/F = B mu0^k mu^(k - 1), fitted where `good`. Each band of
    latitude, numbered in `bands`, with at least `BAND_CELLS` good cells, has a brightness B of its own,
    so that the bands' own brightness, such as the dark equator where the sun stands highest, doesn't
    count as limb darkening."""
    x = np.log(mu0[good] * mu[good])
    y = np.log(radiance[good] * mu[good])
    band = bands[good]
    cells = np.bincount(band)
    x -= (np.bincount(band, x) / np.maximum(cells, 1))[band]
    y -= (np.bincount(band, y) / np.maximum(cells, 1))[band]
    kept = cells[band] >= BAND_CELLS
    return np.sum(x[kept] * y[kept]) / np.sum(x[kept] ** 2)
