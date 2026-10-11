"""GOES-R's full-disk pictures, shared by `limb.py` and `compose.py`: each band's I/F, and the cosines
of the angles of view and light and the phase angle, binned onto latitude and longitude.

- The multi-band product holds each band's I/F at 2 km a pixel, as a reflectance factor that isn't
  divided by the cosine of the sun's angle.
- Each pixel's latitude and longitude come from the scan angles of the GOES-R fixed grid. The cosines
  and the phase angle (the angle between the sun and the satellite, seen from the ground) come from
  the satellite's place and the sun's at the time.
"""
import h5py
import numpy as np

# The bands used and their wavelengths, nm: blue and red. The satellites have no green band.
BANDS = {'CMI_C01': 470.0, 'CMI_C02': 640.0}
# The cells, degrees; the least pixels a cell needs; and the pictures' pixels taken, every this many.
CELL = 0.25
LEAST_PIXELS = 4
EVERY = 2


def scaled(var):
    """A variable's values, unsigned where it says so and scaled, NaN where it holds none."""
    raw = var[::EVERY, ::EVERY] if var.ndim == 2 else var[::EVERY]
    if var.attrs.get('_Unsigned') == b'true':
        raw = raw.astype(np.uint16)
    fill = var.attrs.get('_FillValue')
    values = raw * float(var.attrs.get('scale_factor', [1.0])[0]) + float(var.attrs.get('add_offset', [0.0])[0])
    if fill is not None:
        values = np.where(raw == np.array(fill).astype(raw.dtype), np.nan, values)
    return values


def sun(seconds):
    """The point below the sun, latitude and east longitude in degrees, at `seconds` after J2000 (the
    Astronomical Almanac's low-precision formulas)."""
    n = seconds / 86400.0
    mean_longitude = np.radians(280.460 + 0.9856474 * n)
    anomaly = np.radians(357.528 + 0.9856003 * n)
    ecliptic = mean_longitude + np.radians(1.915) * np.sin(anomaly) + np.radians(0.020) * np.sin(2 * anomaly)
    obliquity = np.radians(23.439 - 0.0000004 * n)
    declination = np.arcsin(np.sin(obliquity) * np.sin(ecliptic))
    right_ascension = np.arctan2(np.cos(obliquity) * np.sin(ecliptic), np.cos(ecliptic))
    sidereal = np.radians(280.46061837 + 360.98564736629 * n)
    return np.degrees(declination), (np.degrees(right_ascension - sidereal) + 180) % 360 - 180


def grid():
    """The latitudes and east longitudes of the cells' centres, degrees: rows from the north, columns
    from 180 degrees west."""
    rows, columns = round(180 / CELL), round(360 / CELL)
    return 90 - (np.arange(rows) + 0.5) * CELL, -180 + (np.arange(columns) + 0.5) * CELL


def binned(path):
    """A picture's bands' I/F, its cosines of view (`mu`) and light (`mu0`) and its phase angle
    (`phase`, degrees), each the mean over a cell of `CELL` degrees, in rows and columns as `grid`
    gives them, NaN where the cell has fewer than `LEAST_PIXELS` pixels; and the sun's place."""
    with h5py.File(path, 'r') as f:
        projection = f['goes_imager_projection'].attrs
        height = float(projection['perspective_point_height'][0])
        a, b = float(projection['semi_major_axis'][0]), float(projection['semi_minor_axis'][0])
        origin = np.radians(float(projection['longitude_of_projection_origin'][0]))
        x, y = np.meshgrid(scaled(f['x']), scaled(f['y']))
        bands = {name: scaled(f[name]) for name in BANDS}
        seconds = float(f['t'][()])
    # Where each line of sight meets the ellipsoid (the GOES-R Product Definition and Users' Guide).
    H = height + a
    qa = np.sin(x) ** 2 + np.cos(x) ** 2 * (np.cos(y) ** 2 + (a / b) ** 2 * np.sin(y) ** 2)
    qb = -2 * H * np.cos(x) * np.cos(y)
    qc = H ** 2 - a ** 2
    disc = qb ** 2 - 4 * qa * qc
    on = disc > 0
    rs = (-qb - np.sqrt(np.where(on, disc, 0))) / (2 * qa)
    sx, sy, sz = rs * np.cos(x) * np.cos(y), -rs * np.sin(x), rs * np.cos(x) * np.sin(y)
    lat = np.arctan((a / b) ** 2 * sz / np.sqrt((H - sx) ** 2 + sy ** 2))
    lon = origin - np.arctan(sy / (H - sx))
    # The surface's normal and the point's place, from the geodetic latitude, and the satellite's.
    normal = np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], axis=-1)
    n_e = a / np.sqrt(1 - (1 - (b / a) ** 2) * np.sin(lat) ** 2)
    point = np.stack([n_e * np.cos(lat) * np.cos(lon), n_e * np.cos(lat) * np.sin(lon),
                      n_e * (b / a) ** 2 * np.sin(lat)], axis=-1)
    to_satellite = np.array([H * np.cos(origin), H * np.sin(origin), 0.0]) - point
    to_satellite /= np.linalg.norm(to_satellite, axis=-1, keepdims=True)
    sun_lat, sun_lon = sun(seconds)
    to_sun = np.array([np.cos(np.radians(sun_lat)) * np.cos(np.radians(sun_lon)),
                       np.cos(np.radians(sun_lat)) * np.sin(np.radians(sun_lon)), np.sin(np.radians(sun_lat))])
    values = dict(bands)
    values['mu'] = np.sum(normal * to_satellite, axis=-1)
    values['mu0'] = normal @ to_sun
    values['phase'] = np.degrees(np.arccos(np.clip(to_satellite @ to_sun, -1, 1)))
    lats, lons = grid()
    rows, columns = len(lats), len(lons)
    good = on & np.all([np.isfinite(band) for band in bands.values()], axis=0)
    cell = (np.clip(((90 - np.degrees(lat[good])) / CELL).astype(int), 0, rows - 1) * columns
            + ((np.degrees(lon[good]) + 180) % 360 / CELL).astype(int) % columns)
    count = np.bincount(cell, minlength=rows * columns)
    out = {}
    for name, v in values.items():
        total = np.bincount(cell, weights=v[good], minlength=rows * columns)
        out[name] = np.where(count >= LEAST_PIXELS, total / np.maximum(count, 1), np.nan).reshape(rows, columns)
    return out, (sun_lat, sun_lon)
