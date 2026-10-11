"""Composes Earth's texture, `width` wide and half as high: north at the top and east to the right, as
`sphere.py`'s spheres map it, with 0 degrees east in the middle column. It comes from NASA's Blue
Marble of 2002 with its clouds, with the haze of the air added back as GOES-18 sees it (`goes.py`).

    python3 compose.py data out.png <width> <brightness> <key light blue>

- The Blue Marble shows the red, green and blue bands of MODIS, at 645, 555 and 469 nm, as sRGB's
  red, green and blue, as NASA's true-colour pictures of Earth do, with the haze of the air taken out.
  Its values, decoded from sRGB, are taken to be proportional to the reflectance in those bands. Its
  columns run east from 180 degrees west, so 0 degrees east is already in the middle.
- Unlike the other bodies' spectra, its three bands aren't taken through the CIE 1931 observer: three
  points hold too little of a spectrum, and drawn straight between them, the forests' narrow green
  peak would turn olive.
- Seen from space, the haze lies over everything and lights up the sea most. Over the South Pacific
  (`REGION`), away from the sun's glint, GOES-18's picture and the Blue Marble are compared on the
  clear sea, the darkest `SEA` of the region in red and in luminance, and on thick clouds, the
  brightest `CLOUDS`.
- Each band is the Blue Marble's, times a transmission t, plus a haze H, with t = 1 in red, so that
  the sea's brightness against the clouds' matches GOES-18's: its blue band at 470 nm against the Blue
  Marble's blue, and its red at 640 against the Blue Marble's red. The game draws every texel with the
  same limb law, so the texture keeps the ratios GOES-18 saw there, with the sun about 37 degrees
  high, the view 54 degrees high and a phase angle of 19 degrees.
- The haze follows a power of the wavelength through the two bands, and t follows the optical depth
  of the air's Rayleigh scattering, which goes as the fourth power; both give the green band's value.
- `brightness` is the texture's mean luminance in linear light, for the game. `key light blue` is the
  blue of the only light that reaches a planet in StarLancer, (1, 1, 0.8): the texture's blue is
  divided by it. If that takes the brightest texels past 1, the whole map is scaled down until all
  but `CLIPPED` of them fit.
"""
import glob
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import globe  # noqa: E402
import goes  # noqa: E402
import truecolour as tc  # noqa: E402

data, out = sys.argv[1:3]
size, brightness, key_blue = int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])

BLUE_MARBLE = 'land_ocean_ice_cloud_8192.tif'
# The wavelengths of the bands of MODIS that the Blue Marble's red, green and blue show, nm. GOES's
# blue and red bands, at 470 and 640 nm, stand for the blue and the red.
RED, GREEN, BLUE = 645.0, 555.0, 469.0
# The region of the sea compared: its latitudes and east longitudes, degrees; and the least angle a
# cell of GOES-18's picture is from the sun's glint, degrees.
REGION = dict(lat=(-40.0, -12.0), lon=(-165.0, -115.0))
LEAST_GLINT = 30.0
# The share of the region taken as clear sea, the darkest, and as thick clouds, the brightest.
SEA = 0.05
CLOUDS = 0.03
# The share of the texels that may be clipped.
CLIPPED = 0.001


def sea_and_clouds(values, brightness):
    """The medians of `values`, the last axis each band or channel, over the darkest `SEA` and the
    brightest `CLOUDS` of the cells by `brightness`."""
    sea = brightness <= np.quantile(brightness, SEA)
    clouds = brightness >= np.quantile(brightness, 1 - CLOUDS)
    return np.median(values[sea], axis=0), np.median(values[clouds], axis=0)


# GOES-18's picture over the region, away from the glint: where the surface's normal is more than
# `LEAST_GLINT` from halfway between the sun and the satellite.
path = glob.glob(f"{data}/OR_ABI-L2-MCMIPF-*_G18_*.nc")[0]
cells, _ = goes.binned(path)
lats, lons = goes.grid()
lat, lon = np.meshgrid(lats, lons, indexing='ij')
halfway = (cells['mu'] + cells['mu0']) / (2 * np.cos(np.radians(cells['phase']) / 2))
glint = np.degrees(np.arccos(np.clip(halfway, -1, 1)))
region = ((lat > REGION['lat'][0]) & (lat < REGION['lat'][1]) & (lon > REGION['lon'][0]) & (lon < REGION['lon'][1])
          & np.isfinite(cells['CMI_C02']) & (glint > LEAST_GLINT))
measured = np.stack([cells['CMI_C02'][region], cells['CMI_C01'][region]], axis=-1)
goes_sea, goes_clouds = sea_and_clouds(measured, measured[:, 0])
print(f"GOES-18 over the region: sun {np.degrees(np.arcsin(np.median(cells['mu0'][region]))):.0f} degrees high, view "
      f"{np.degrees(np.arcsin(np.median(cells['mu'][region]))):.0f}, phase {np.median(cells['phase'][region]):.0f}; "
      f"the sea against the clouds: {goes_sea[1] / goes_clouds[1]:.3f} in blue, {goes_sea[0] / goes_clouds[0]:.3f} in red")

# The Blue Marble in linear light at the texture's size, and over the same region.
w, h = size, size // 2
raw = subprocess.run(['magick', f"{data}/{BLUE_MARBLE}", '-colorspace', 'RGB', '-resize', f'{w}x{h}!', '-depth', '16', 'rgb:-'],
                     capture_output=True, check=True).stdout
marble = np.frombuffer(raw, '<u2').reshape(h, w, 3).astype(np.float32) / 65535
tex_lats = 90 - (np.arange(h) + 0.5) * 180 / h
tex_lons = -180 + (np.arange(w) + 0.5) * 360 / w
rows = (tex_lats > REGION['lat'][0]) & (tex_lats < REGION['lat'][1])
columns = (tex_lons > REGION['lon'][0]) & (tex_lons < REGION['lon'][1])
part = marble[rows][:, columns].reshape(-1, 3)
marble_sea, marble_clouds = sea_and_clouds(part, tc.luminance(part))
print(f"the Blue Marble over the region: the sea against the clouds {np.round(marble_sea / marble_clouds, 3)} in red, green and blue")

# Red: t = 1, and the scale from the Blue Marble to GOES-18's I/F, with the haze. Blue: t and the
# haze.
scale = (goes_clouds[0] - goes_sea[0]) / (marble_clouds[0] - marble_sea[0])
haze_red = goes_sea[0] / scale - marble_sea[0]
through_blue = (goes_clouds[1] - goes_sea[1]) / (scale * (marble_clouds[2] - marble_sea[2]))
haze_blue = goes_sea[1] / scale - through_blue * marble_sea[2]
power = np.log(haze_blue / haze_red) / np.log(RED / BLUE)


def haze(lam):
    return haze_blue * (lam / BLUE) ** -power


def through(lam):
    return through_blue ** ((lam ** -4.0 - RED ** -4.0) / (BLUE ** -4.0 - RED ** -4.0))


print(f"the haze: {haze_blue:.4f} in blue, {haze(GREEN):.4f} in green and {haze_red:.4f} in red, as the wavelength to the "
      f"-{power:.2f}; what it lets through: {through_blue:.3f} in blue and {through(GREEN):.3f} in green")

# Each band through the haze, as sRGB's red, green and blue.
texture = (marble * np.array([through(RED), through(GREEN), through(BLUE)], np.float32)
           + np.array([haze(RED), haze(GREEN), haze(BLUE)], np.float32))
del marble

mean = np.array([globe.area_mean(texture[..., c], np.ones(h, dtype=bool), tex_lats) for c in range(3)])
texture *= brightness / tc.luminance(mean)
print(f"the mean colour, at the texture's brightness of {brightness}: 8-bit sRGB "
      f"{np.round(tc.encode(mean * brightness / tc.luminance(mean)) * 255).astype(int)}")
texture[..., 2] /= key_blue
fit = max(1.0, float(np.quantile(texture[::4, ::4], 1 - CLIPPED)))
texture /= fit
print(f"scaled down by {fit:.3f} to fit")

pixels = (np.clip(texture, 0, 1) * 65535 + 0.5).astype('<u2')
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '16', '-endian', 'LSB', 'rgb:-', '-set', 'colorspace', 'RGB',
                '-colorspace', 'sRGB', '-depth', '8', '-define', 'png:exclude-chunks=date,time', out],
               input=pixels.tobytes(), check=True)
print('wrote', out)
