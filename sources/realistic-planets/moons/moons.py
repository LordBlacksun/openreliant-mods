"""Jupiter's moons and Triton as their maps and Voyager's frames show them, shared by `fit.py` and
`compose.py`: each moon's map and shape, the camera's filters, and each frame's view of its moon."""
import os
import subprocess

import numpy as np
from scipy import ndimage

import voyager

# The value the USGS's maps of Jupiter's moons rise from in proportion to the ground's brightness: the
# GeoTIFF tags' offset over their scale, for Io's, Europa's and Ganymede's maps. Callisto's map
# carries no such tags, and is taken to rise from the same.
USGS_ZERO = 0.5
# Each moon's map; from its GeoTIFF tags, the radius of the sphere it's mapped on, km, and the east
# longitude of its left edge; the value its brightness rises from; and its visual geometric albedo
# (NASA's Jovian and Neptunian Satellite Fact Sheets). Triton's map is in colour, its bands made from
# Voyager 2's orange, violet and ultraviolet frames; its middle band, the violet one, is read
# (`band`), as of the three it matches Voyager's green frames best. Its contrast was stretched for
# display, and its zero isn't known, so `compose.py` fits it to the green frames. Voyager 2 saw only
# Triton's south and a little of its north, so the rest of the north is filled with a guess
# (`mirror`, `mirrored`).
MOONS = {
    'Io': dict(map='Io_Galileo_SSI_Global_Mosaic_1km.tif', radius=1821.46, left=-180.0, zero=USGS_ZERO, albedo=0.62),
    'Europa': dict(map='Europa_Voyager_GalileoSSI_global_mosaic_500m.tif', radius=1562.09, left=0.0, zero=USGS_ZERO,
                   albedo=0.68),
    'Ganymede': dict(map='Ganymede_Voyager_GalileoSSI_global_mosaic_1km.tif', radius=2632.34, left=0.0, zero=USGS_ZERO,
                     albedo=0.44),
    'Callisto': dict(map='Callisto_Voyager_GalileoSSI_global_mosaic_1km.tif', radius=2409.30, left=0.0, zero=USGS_ZERO,
                     albedo=0.19),
    'Triton': dict(map='Triton_Voyager2_ClrMosaic_GlobalFill_600m.tif', radius=1350.0, left=-180.0, zero=None, albedo=0.72,
                   band='G', mirror=True),
}
# The narrow-angle camera's filters and their effective wavelengths, nm.
FILTERS = {'Violet': 416.0, 'Blue': 479.0, 'Green': 566.0, 'Orange': 591.0}
# The step of the reduced map that frames are matched against, degrees.
REDUCED_STEP = 0.25
# How far the guess for ground no picture saw blends in from what was seen nearest, degrees.
MIRROR_BLEND = 10.0
# A difference from its neighbours' median, I/F, past which a frame's pixel is taken as bad.
BAD_PIXEL = 0.02
# Where a frame's sky is measured, beyond this many of the disk's radii from its centre, and the
# least pixels it needs.
SKY_FROM = 1.2
SKY_PIXELS = 2000


def frame(data, entry):
    """A frame's image as I/F, its single bad pixels given their neighbours' median, and its pixel's
    size in radians."""
    name = entry['name']
    img, fields = voyager.image(f"{data}/{name}_GEOMED.IMG", f"{data}/{name}_GEOMED.LBL")
    median = ndimage.median_filter(img, size=3)
    return np.where(np.abs(img - median) > BAD_PIXEL, median, img), voyager.pixel(fields)


def sky(img, view):
    """The level of the frame's sky, which is taken off the frame: most frames read within half a per
    cent of the disk's brightness there, but a few several per cent. 0 where too little sky shows."""
    radius = view.body.a / np.linalg.norm(view.observer) / view.pixel * view.scale
    ys, xs = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    far = (np.hypot(xs - view.cx, ys - view.cy) > SKY_FROM * radius) & (voyager.frame_mask(img) > 0)
    return float(np.median(img[far])) if far.sum() >= SKY_PIXELS else 0.0


def body(moon):
    return voyager.Body(MOONS[moon]['radius'], MOONS[moon]['radius'])


def read_map(data, moon):
    """The moon's map, or its `band`, as 8-bit values, 0 where it holds nothing: north at the top,
    east longitude rising to the right from `left` at the left edge."""
    path = os.path.join(data, MOONS[moon]['map'])
    size = subprocess.run(['magick', 'identify', '-format', '%w %h', path], capture_output=True, check=True, text=True).stdout
    w, h = (int(v) for v in size.split())
    band = ['-channel', MOONS[moon]['band'], '-separate'] if 'band' in MOONS[moon] else []
    raw = subprocess.run(['magick', path, *band, '-depth', '8', 'gray:-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w)


def reduce(values, step):
    """A map brought to cells of `step` degrees, each the mean of the values it covers that hold
    something, NaN where none does."""
    h, w = values.shape
    rows, columns = round(180 / step), round(360 / step)
    y = np.arange(h) * rows // h
    x = np.arange(w) * columns // w
    total = np.zeros(rows * columns)
    count = np.zeros(rows * columns)
    for start in range(0, h, 512):
        part = values[start:start + 512]
        cell = y[start:start + 512, None] * columns + x[None, :]
        held = part > 0
        total += np.bincount(cell[held], weights=part[held], minlength=rows * columns)
        count += np.bincount(cell[held], minlength=rows * columns)
    return np.where(count > 0, total / np.maximum(count, 1), np.nan).reshape(rows, columns)


def east_at_left(reduced, moon):
    """A reduced map turned round so that 0 degrees east is at its left edge."""
    columns = reduced.shape[1]
    return np.roll(reduced, round(MOONS[moon]['left'] / 360 * columns), axis=1)


def lookup(reduced, lat, lon):
    """The reduced map's value at planetocentric latitudes and east longitudes, degrees, bilinear
    and wrapping round in longitude; NaN where the map holds nothing."""
    rows, columns = reduced.shape
    step = 180 / rows
    y = (90 - lat) / step - 0.5
    x = (lon % 360) / step - 0.5
    filled = np.nan_to_num(reduced)
    held = np.isfinite(reduced).astype(float)
    wrapped = np.concatenate([filled, filled[:, :1]], axis=1)
    held_wrapped = np.concatenate([held, held[:, :1]], axis=1)
    x = np.where(x < 0, x + columns, x)
    value = ndimage.map_coordinates(wrapped, [y, x], order=1, mode='nearest')
    weight = ndimage.map_coordinates(held_wrapped, [y, x], order=1, mode='nearest')
    return np.where(weight > 0.99, value / np.maximum(weight, 1e-9), np.nan)


def mirrored(grid, step):
    """A latitude-longitude map, its rows `step` degrees apart, filled where it holds nothing with the
    map at the opposite latitude, 180 degrees round: a guess for ground that no picture saw, from
    ground of the same kind and latitude. Within `MIRROR_BLEND` degrees of what the map holds, the
    guess blends in from that, smoothed."""
    held = np.isfinite(grid)
    opposite = np.roll(grid[::-1], grid.shape[1] // 2, axis=1)
    sigma = MIRROR_BLEND / 2 / step
    total = ndimage.gaussian_filter(np.where(held, grid, 0.0), sigma, mode=('nearest', 'wrap'))
    count = ndimage.gaussian_filter(held.astype(float), sigma, mode=('nearest', 'wrap'))
    nearby = np.where(count > 1e-9, total / np.maximum(count, 1e-9), opposite)
    share = np.clip(ndimage.distance_transform_edt(~held) * step / MIRROR_BLEND, 0, 1)
    return np.where(held, grid, (1 - share) * nearby + share * opposite)


def lat_lon(p):
    """Planetocentric latitudes and east longitudes, degrees, of body-fixed points."""
    r = np.linalg.norm(p, axis=-1)
    return np.rad2deg(np.arcsin(np.clip(p[..., 2] / r, -1, 1))), np.rad2deg(np.arctan2(p[..., 1], p[..., 0])) % 360
