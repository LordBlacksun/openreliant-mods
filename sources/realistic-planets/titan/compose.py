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
- Each frame's disk is fitted to its lit limb, where the brightness falls to half of that just
  inside it. That's the haze's edge in the filter, at 28 to 33 degrees of phase about 2,710 km from
  the centre in red, 2,730 km in green and 2,840 km in blue, and about 30 km higher at 50 degrees.
  The game's sphere stands for green's, 2,741 km over the four sets (`haze.py`).
- Each pixel's latitude and the cosines of its angles of light and view come from the disk, the
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
import subprocess
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import cassini  # noqa: E402
import globe  # noqa: E402
import minnaert  # noqa: E402
import truecolour as tc  # noqa: E402

data, listing, spectrum, out = sys.argv[1:5]
surface, brightness, key_blue = float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7])

# The least height of the sun, and of the view above the limb, where a frame is used, degrees; the
# bands of latitude the haze is measured in, degrees; and the latitudes each frame's mean is taken
# within.
LEAST_HEIGHT = 15.0
BAND = 5.0
MEAN_LATITUDE = 60.0
# The surface map's degrees a pixel, and the columns wrapped round either side of it for the cubic
# interpolation across its edges.
SURFACE_STEP = 1 / 16
WRAP = 4
# The share of texels allowed past 1, and so clipped, if the map has to be scaled down to fit.
CLIPPED = 0.001
# The texture's size, and the rows it's made in at a time, to save memory.
SIZE = (8192, 4096)
STRIP = 512


# Each frame's limb, exponent and profile.
with open(listing) as f:
    frames = json.load(f)['frames']
centres = np.arange(-90 + BAND / 2, 90, BAND)
weights = np.cos(np.radians(centres))
exponents, profiles, means = ({f: [] for f in cassini.FILTERS} for _ in range(3))
least = np.sin(np.radians(LEAST_HEIGHT))
for f in frames:
    image = cassini.trusted(cassini.frame(os.path.join(data, os.path.basename(f['urls'][1]))))
    cx, cy, radius = cassini.limb(image, f)
    lat, mu, mu0, disk = cassini.geometry(image.shape, cx, cy, radius, f)
    good = disk & (image > 0) & (mu > least) & (mu0 > least)
    bands = np.clip(((lat + 90) // BAND).astype(int), 0, len(centres) - 1)
    k, b = minnaert.fit(image, np.where(good, mu0, 1), np.where(good, mu, 1), good, bands)
    b = np.append(b, [np.nan] * (len(centres) - len(b)))
    seen = np.isfinite(b) & (np.abs(centres) <= MEAN_LATITUDE)
    mean_log = np.sum(np.log(b[seen]) * weights[seen]) / weights[seen].sum()
    exponents[f['filter']].append(k)
    profiles[f['filter']].append(np.log(b) - mean_log)
    means[f['filter']].append(mean_log)
    print(f"{f['name']} ({f['filter']}, {f['time'][:10]}, phase {f['phase']:.0f} degrees): the haze's edge {radius * f['resolution_km']:.0f} km "
          f"from the centre, Minnaert's exponent {k:.3f}, the bands seen from {centres[np.isfinite(b)].min():+.1f} to {centres[np.isfinite(b)].max():+.1f}")

# Each filter's profile, and its exponent.
profile = {}
for name, wavelength in cassini.FILTERS.items():
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
by_wavelength = sorted(cassini.FILTERS, key=cassini.FILTERS.get)
limb_exponents = np.interp(channels, [cassini.FILTERS[n] for n in by_wavelength], [np.mean(exponents[n]) for n in by_wavelength])
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
scale = brightness / globe.area_mean(tc.luminance(texture), np.ones(h, dtype=bool), lats)
texture *= scale
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

# For haze.py: what the I/F in each filter becomes in the texture's linear sRGB, as a band's
# brightness over the frames' mean bends the spectrum, with its blue divided by the key light's as the
# texture's is, since the sun lights the haze as it lights the disk.
key_light = np.array([1.0, 1.0, 1.0 / key_blue])
colours = {name: (scale / fit * K[wavelength] / np.exp(np.mean(means[name])) * key_light).tolist() for name, wavelength in cassini.FILTERS.items()}
with open(os.path.join(data, 'colour.json'), 'w') as f:
    json.dump({'about': "Titan's I/F in each of Cassini's filters as the texture's linear sRGB, its blue divided by "
                        "the key light's: a row for each filter.", 'colours': colours}, f, indent=1)
print('the texture\'s linear sRGB for an I/F of 1 in each filter:',
      {name: np.round(c, 5).tolist() for name, c in colours.items()})
