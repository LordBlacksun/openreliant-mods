"""True colour from a reflectance spectrum: the CIE 1931 2-degree observer (Wyman, Sloan and Shirley's
2013 analytic fit), sunlight as a 5778 K blackbody, a white reflector adapted to D65 white with the
Bradford transform, and the sRGB primaries."""
import numpy as np


def _g(lam, mu, s1, s2):
    s = np.where(lam < mu, s1, s2)
    return np.exp(-0.5 * ((lam - mu) / s) ** 2)


def cmf(lam):
    x = 1.056 * _g(lam, 599.8, 37.9, 31.0) + 0.362 * _g(lam, 442.0, 16.0, 26.7) - 0.065 * _g(lam, 501.1, 20.4, 26.2)
    y = 0.821 * _g(lam, 568.8, 46.9, 40.5) + 0.286 * _g(lam, 530.9, 16.3, 31.1)
    z = 1.217 * _g(lam, 437.0, 11.8, 36.0) + 0.681 * _g(lam, 459.0, 26.0, 13.8)
    return np.stack([x, y, z], axis=-1)


def sun(lam, temperature=5778.0):
    h, c, k = 6.62607015e-34, 2.99792458e8, 1.380649e-23
    l = lam * 1e-9
    return 1.0 / (l ** 5 * (np.exp(h * c / (l * k * temperature)) - 1.0))


BRADFORD = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])
D65 = np.array([0.95047, 1.0, 1.08883])
XYZ_TO_SRGB = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])


def matrix(lam):
    """The matrix that turns a spectrum's reflectances at wavelengths lam (nm, evenly spaced) into
    linear sRGB, a perfect white reflector giving (1, 1, 1)."""
    w = cmf(lam) * sun(lam)[:, None]
    white = w.sum(axis=0)
    white = white / white[1]
    src, dst = BRADFORD @ white, BRADFORD @ D65
    adapt = np.linalg.inv(BRADFORD) @ np.diag(dst / src) @ BRADFORD
    to_rgb = XYZ_TO_SRGB @ adapt
    per_wavelength = (to_rgb @ (w / w[:, 1].sum()).T).T     # each wavelength's share of R, G and B
    return per_wavelength


def encode(linear):
    linear = np.clip(linear, 0, 1)
    return np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055)
