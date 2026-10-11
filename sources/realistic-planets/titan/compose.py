"""Composes Titan's texture as an 8192x4096 sRGB PNG: north at the top and east to the right, as
`sphere.py`'s spheres map it, with 0 degrees east in the middle column. The colour and the bands of
its haze come from Cassini's frames and Karkoschka's spectrum, and its surface, which the haze hides
from the eye, from Cassini's map at 938 nm, shown faintly. It also prints the limb's exponents for
the mod's `planets.luau`.

    python3 compose.py data frames.json data/1993.tab out.png <surface> <brightness> <key light blue>

The haze:

- Cassini's narrow-angle camera took four sets of frames of Titan in its blue, green and red filters
  in January and February 2010, months after Titan's equinox, with the sun over its equator and both
  poles lit. `frames.json` lists them, calibrated to I/F, with their geometry. Titan is about 800
  pixels across in them, at phase angles of 28 to 50 degrees.
- Each frame's disc is fitted to its lit limb, where the brightness falls to half of that just
  inside it. That's the haze's edge in the filter, about 2,710 km from the centre in red and green
  and 2,840 km in blue, and it's the sphere the game draws.
- Each pixel's latitude and the cosines of its angles of light and view come from the disc, the
  frame's sub-spacecraft and sub-solar points, and the clock angle of Titan's pole in the frame.
- Minnaert's law is fitted to each frame where the sun is more than `LEAST_HEIGHT` degrees up and
  the view more than that above the limb, each band of `BAND` degrees of latitude with its own
  brightness (`minnaert.py`). A band's brightness over the frame's mean within `MEAN_LATITUDE` degrees
  of the equator is the haze's profile in that filter. The sets' profiles are averaged on the
  logarithm and held at their last values past the last bands seen.
- The exponents of each filter, averaged, give the limb's at each channel's wavelength for Titan's
  spectrum, for `planets.luau`.

The colour, the surface and the brightness:

- The colour is true colour (`truecolour.py`) of Karkoschka's albedo spectrum of Titan, bent at each
  latitude through the three filters' profiles, as Saturn's is through its maps.
- Cassini's map of the surface at 938 nm (PIA22770), from 9,873 frames taken over 13 years, holds
  the surface's normal albedo, the haze taken out with a model of it, at 16 pixels a degree. Its
  columns run east from 0 degrees at the left edge. To the eye the haze hides the surface entirely.
  `surface` is the share of the map's contrast, on the logarithm, that the texture shows through the
  haze's colour: 0 gives the haze alone.
- `brightness` is the texture's mean luminance in linear light, for the game.
- `key light blue` is the blue of the only light that reaches a planet in StarLancer, (1, 1, 0.8):
  the texture's blue is divided by it, so that the planet shows its own colour in the game. If that
  takes the brightest texels past 1, the whole map is scaled down until all but `CLIPPED` of them fit.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import globe  # noqa: E402
import minnaert  # noqa: E402
import truecolour as tc  # noqa: E402

data, listing, spectrum, out = sys.argv[1:5]
surface, brightness, key_blue = float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7])

# Cassini's blue, green and red filters' effective wavelengths, nm, as for Saturn's maps (Wang and
# others, 2025).
FILTERS = {'BL1': 463.0, 'GRN': 568.0, 'RED': 647.0}
# The highest I/F a frame's pixel can hold and be trusted: a higher one is a hot pixel or a cosmic ray.
MOST_IF = 5.0
# The least height of the sun, and of the view above the limb, where a frame is used, degrees; the
# bands of latitude the haze is measured in, degrees; and the latitudes each frame's mean is taken
# within.
LEAST_HEIGHT = 15.0
BAND = 5.0
MEAN_LATITUDE = 60.0
# The limb fit. The first guess at the disc is the pixels brighter than `FIRST_GUESS` of the 99th
# percentile. Rays `RAY_STEP` degrees apart run from the centre over `RAY_REACH` of the radius, in
# `RAY_SAMPLES` steps, and the edge is where a ray's brightness falls to `EDGE` of its median between
# `PLATEAU` of the radius. A ray counts where the sun's cosine at `LIT_AT` of the radius is at least
# `LIT_LIMB`. The fit is repeated `FITS` times from the last disc.
FIRST_GUESS = 0.4
RAY_STEP = 0.5
RAY_REACH = (0.6, 1.4)
RAY_SAMPLES = 401
EDGE = 0.5
PLATEAU = (0.8, 0.9)
LIT_AT = 0.98
LIT_LIMB = 0.3
FITS = 4
# The surface map's degrees a pixel, and the columns wrapped round either side of it for the cubic
# interpolation across its edges.
SURFACE_STEP = 1 / 16
WRAP = 4
# The share of texels allowed past 1, and so clipped, if the map has to be scaled down to fit.
CLIPPED = 0.001
# The texture's size, and the rows it's made in at a time, to save memory.
SIZE = (8192, 4096)
STRIP = 512


def frame(label):
    """A calibrated frame's I/F, from its detached PDS3 label, and its filter's name."""
    with open(label, encoding='latin-1') as f:
        text = f.read()
    record = int(re.search(r'^\s*RECORD_BYTES\s*=\s*(\d+)', text, re.M).group(1))
    start = int(re.search(r'\^IMAGE\s*=\s*\("[^"]+",\s*(\d+)\)', text).group(1))
    image = text[re.search(r'OBJECT\s*=\s*IMAGE\s', text).start():]
    lines = int(re.search(r'\bLINES\s*=\s*(\d+)', image).group(1))
    samples = int(re.search(r'\bLINE_SAMPLES\s*=\s*(\d+)', image).group(1))
    data = np.fromfile(label[:-4] + '.IMG', dtype='<f4', count=lines * samples, offset=(start - 1) * record)
    return data.reshape(lines, samples).astype(np.float64)


def unit(lat, lon):
    """The unit vector toward a planetocentric latitude and east longitude, degrees."""
    lat, lon = np.radians(lat), np.radians(lon)
    return np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def geometry(shape, cx, cy, radius, f):
    """Each pixel's latitude and the cosines of its angles of view and light, on a sphere of `radius`
    pixels about (`cx`, `cy`), seen from afar; and where the sphere is."""
    observer, sun = unit(f['observer_lat'], f['observer_east_lon']), unit(f['sun_lat'], f['sun_east_lon'])
    north = np.array([0.0, 0.0, 1.0]) - observer[2] * observer
    north /= np.linalg.norm(north)
    across = np.cross(observer, north)
    t = np.radians(f['north_clock_angle'])
    right, up = np.sin(t) * north - np.cos(t) * across, np.cos(t) * north + np.sin(t) * across
    lines, samples = np.indices(shape).astype(np.float64)
    x, y = (samples - cx) / radius, (cy - lines) / radius
    disc = x ** 2 + y ** 2 < 1
    mu = np.sqrt(np.clip(1 - x ** 2 - y ** 2, 0, None))
    point = x[..., None] * right + y[..., None] * up + mu[..., None] * observer
    return np.degrees(np.arcsin(np.clip(point[..., 2], -1, 1))), mu, point @ sun, disc


def limb(image, f):
    """The disc's centre and radius, pixels, fitted to the lit limb: along rays from the centre, where
    the brightness falls to `EDGE` of that just inside, and a circle through those points."""
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
        edges = np.array(edges)
        (cx, cy, c), *_ = np.linalg.lstsq(np.c_[2 * edges, np.ones(len(edges))], (edges ** 2).sum(axis=1), rcond=None)
        radius = np.sqrt(c + cx ** 2 + cy ** 2)
    return cx, cy, radius


# Each frame's limb, exponent and profile.
with open(listing) as f:
    frames = json.load(f)['frames']
centres = np.arange(-90 + BAND / 2, 90, BAND)
weights = np.cos(np.radians(centres))
exponents, profiles = {f: [] for f in FILTERS}, {f: [] for f in FILTERS}
least = np.sin(np.radians(LEAST_HEIGHT))
for f in frames:
    image = frame(os.path.join(data, os.path.basename(f['urls'][1])))
    image = np.where(np.isfinite(image) & (image > 0) & (image < MOST_IF), image, 0)
    cx, cy, radius = limb(image, f)
    lat, mu, mu0, disc = geometry(image.shape, cx, cy, radius, f)
    good = disc & (image > 0) & (mu > least) & (mu0 > least)
    bands = np.clip(((lat + 90) // BAND).astype(int), 0, len(centres) - 1)
    k, b = minnaert.fit(image, np.where(good, mu0, 1), np.where(good, mu, 1), good, bands)
    b = np.append(b, [np.nan] * (len(centres) - len(b)))
    seen = np.isfinite(b) & (np.abs(centres) <= MEAN_LATITUDE)
    exponents[f['filter']].append(k)
    profiles[f['filter']].append(np.log(b) - np.sum(np.log(b[seen]) * weights[seen]) / weights[seen].sum())
    print(f"{f['name']} ({f['filter']}, {f['time'][:10]}, phase {f['phase']:.0f} degrees): the haze's edge {radius * f['resolution_km']:.0f} km "
          f"from the centre, Minnaert's exponent {k:.3f}, the bands seen from {centres[np.isfinite(b)].min():+.1f} to {centres[np.isfinite(b)].max():+.1f}")

# Each filter's profile, and its exponent.
profile = {}
for name, wavelength in FILTERS.items():
    logs = np.array(profiles[name])
    seen = np.isfinite(logs).any(axis=0)
    mean = np.nanmean(np.where(np.isfinite(logs), logs, np.nan)[:, seen], axis=0)
    profile[wavelength] = np.interp(centres, centres[seen], mean)
    print(f"{name} at {wavelength:.0f} nm: Minnaert's exponent {np.mean(exponents[name]):.3f}; the haze's brightness over its mean, "
          + " ".join(f"{c:+.0f}:{np.exp(p):.2f}" for c, p in zip(centres[::2], profile[wavelength][::2])))

# The spectrum bent through each filter by hat functions that sum to one, flat beyond them.
lam, albedo = tc.karkoschka(spectrum, 'titan')
M = tc.matrix(lam)
wavelengths = sorted(profile)
hats = dict(zip(wavelengths, tc.hats(lam, wavelengths)))
K = {w: ((albedo * h)[:, None] * M).sum(axis=0) for w, h in hats.items()}
geometric = sum(K.values())

# The limb's exponents at each channel's wavelength for Titan's spectrum.
channels = tc.channels(lam, albedo, M)
limb_exponents = np.interp(channels, [FILTERS[n] for n in sorted(FILTERS, key=FILTERS.get)],
                           [np.mean(exponents[n]) for n in sorted(FILTERS, key=FILTERS.get)])
print(f"the channels' wavelengths for Titan's spectrum: {np.round(channels).astype(int)} nm; their exponents, for planets.luau: "
      f"{np.round(limb_exponents, 3)}")

# The texture's grid: each texel's latitude, and the haze's colour along it.
w, h = SIZE
lats = 90 - (np.arange(h) + 0.5) * 180 / h
haze = sum(np.exp(np.interp(lats, centres, profile[wl]))[:, None] * K[wl] for wl in wavelengths)
print(f"the haze's colour at the equator, linear sRGB {np.round(haze[h // 2], 4)}, as 8-bit sRGB {np.round(tc.encode(haze[h // 2]) * 255).astype(int)}")

# The surface, resampled to the grid, as its ratio to its mean, shown at `surface` of its contrast.
raw = subprocess.run(['magick', f"{data}/PIA22770.tif", '-depth', '16', 'gray:-'], capture_output=True, check=True).stdout
pia_rows, pia_columns = round(180 / SURFACE_STEP), round(360 / SURFACE_STEP)
pia = np.maximum(np.frombuffer(raw, '>u2').reshape(pia_rows, pia_columns).astype(np.float64), 1)
pia_lats = 90 - (np.arange(pia_rows) + 0.5) * SURFACE_STEP
pia /= globe.area_mean(pia, np.ones(pia_rows, dtype=bool), pia_lats)
wrapped = np.log(np.concatenate([pia[:, -WRAP:], pia, pia[:, :WRAP]], axis=1))
row = (np.arange(h) + 0.5) * 180 / h / SURFACE_STEP - 0.5
column = ((np.arange(w) + 0.5) * 360 / w - 180) % 360 / SURFACE_STEP - 0.5 + WRAP
texture = np.empty((h, w, 3), np.float32)
for start in range(0, h, STRIP):
    rr, cc = np.meshgrid(row[start:start + STRIP], column, indexing='ij')
    shade = np.exp(surface * ndimage.map_coordinates(wrapped, [rr, cc], order=3, mode='nearest'))
    texture[start:start + STRIP] = haze[start:start + STRIP, None, :] * shade[..., None]

# At the brightness asked for; the true normal albedo, for reference, from the geometric with Minnaert's
# law, by which the normal albedo is (2k + 1) / 2 times the geometric.
texture *= brightness / globe.area_mean(tc.luminance(texture), np.ones(h, dtype=bool), lats)
normal_over_geometric = (2 * limb_exponents[1] + 1) / 2
print(f"geometric albedo, linear sRGB {np.round(geometric, 4)}, as 8-bit sRGB {np.round(tc.encode(geometric) * 255).astype(int)}; "
      f"true mean luminance at the normal albedo, {normal_over_geometric:.3f} times the geometric by Minnaert's law in green: "
      f"{normal_over_geometric * tc.luminance(geometric):.3f}; in the texture: {brightness:.3f}")
texture[..., 2] /= key_blue
fit = max(1.0, np.quantile(texture[::4, ::4], 1 - CLIPPED))
texture /= fit
print(f"scaled down by {fit:.3f} to fit")
pixels = (np.clip(texture, 0, 1) * 65535 + 0.5).astype('<u2')
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '16', '-endian', 'LSB', 'rgb:-', '-set', 'colorspace', 'RGB',
                '-colorspace', 'sRGB', '-depth', '8', '-define', 'png:exclude-chunks=date,time', out],
               input=pixels.tobytes(), check=True)
print('wrote', out)
