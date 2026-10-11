"""Neptune as Voyager 2's frames see it, on the shared geometry (`voyager.py`): its shape, the
narrow-angle camera's fixed blemishes in 1989, its winds, and the twist found from its bands.
"""
import numpy as np

import voyager

NEPTUNE = voyager.Body(24764.0, 24341.0)    # equatorial and polar radii, km (IAU)
PIXEL = np.deg2rad(4.4930e-4)   # a GEOMED pixel, radians, from the products' labels
# The narrow-angle camera's fixed blemishes, in GEOMED pixels, as `blemishes.py`'s pattern shows
# them: compact rings found with a Laplacian of Gaussian filter and checked by eye, each reaching
# BLEMISH_RADIUS pixels from its centre.
BLEMISHES = [(553, 574), (709, 725), (472, 228), (400, 342), (313, 586)]
BLEMISH_RADIUS = 26


def view(frame, cx=500.0, cy=500.0, twist=0.0, scale=1.0):
    """A frame's view of Neptune (`voyager.View`)."""
    return voyager.View(NEPTUNE, PIXEL, frame, cx, cy, twist, scale)


def wind(lat_g):
    """Neptune's zonal wind relative to System III, m/s, eastward positive (Sromovsky et al. 1993)."""
    return -398.0 + 0.188 * lat_g ** 2 - 1.2e-5 * lat_g ** 4


def drift(lat_g, seconds):
    """How far east, in degrees, the clouds at each latitude move in a time."""
    la = np.deg2rad(lat_g)
    n = NEPTUNE.a / np.sqrt(1 - NEPTUNE.e2 * np.sin(la) ** 2)
    radius = np.maximum(n * np.cos(la), 1.0) * 1000.0
    return np.rad2deg(wind(lat_g) * seconds / radius)


def band_cost(img, view, k, mask):
    """How unevenly the albedo varies along each latitude, robustly: the median absolute deviation
    of each row of the frame's map, squared and averaged. Neptune's bands follow latitude lines, so
    this is least at the frame's true twist, and single clouds such as the Great Dark Spot barely
    move it."""
    lats, lons = np.arange(-72, 30, 0.5), np.arange(0, 360, 0.5)
    a, _, _ = voyager.albedo_grid(img, view, k, lats, lons, least=0.45, mask=mask)
    a = a / np.nanmedian(a)
    total, count = 0.0, 0
    for row in a:
        v = row[np.isfinite(row)]
        if v.size < 60:
            continue
        mad = np.median(np.abs(v - np.median(v)))
        total += mad * mad * v.size
        count += v.size
    return total / count
