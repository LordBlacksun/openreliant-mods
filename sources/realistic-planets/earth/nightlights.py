"""Makes Earth's emissive map, its city lights, `width` wide and half as high, laid out as Earth's
texture is: north at the top, and columns running east from 180 degrees west. It comes from NASA's
Black Marble of 2016, which lays its map out the same way.

    python3 nightlights.py data/night/BlackMarble_2016_3km.jpg out.png <width> <brightness>

- The Black Marble draws the lights over a dark blue picture of the ground and the sea, which isn't
  light the night side gives off, so only the lights are kept. In linear light the ground is always
  bluer than red, by `WARMEST_GROUND` or more, the ratio of Australia's warmest deserts, and the
  lights are warm, `LIGHTS`. Each texel's red, less its blue over `WARMEST_GROUND`, is the lights'
  red, which the ground can't give; texels where it falls below 0 have no lights.
- The map is scaled down in linear light first, so that a town too small for a texel still lights
  it by its share.
- `brightness` scales the lights, in linear light, against the Black Marble's.
"""
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import render  # noqa: E402

source, out = sys.argv[1:3]
width, brightness = int(sys.argv[3]), float(sys.argv[4])

# The blue against the red of the warmest ground in the Black Marble, in linear light: Australia's
# reddest deserts. The rest of the ground and the sea are bluer.
WARMEST_GROUND = 1.9
# The lights' colour in linear light, against their red: the mean of the brightest texels below the
# few that are clipped.
LIGHTS = np.array([1.0, 0.78, 0.61])

height = width // 2
raw = subprocess.run(['magick', source, '-colorspace', 'RGB', '-filter', 'Box', '-resize', f'{width}x{height}!', '-depth', '16',
                      '-endian', 'LSB', 'rgb:-'], capture_output=True, check=True).stdout
linear = np.frombuffer(raw, dtype='<u2').reshape(height, width, 3).astype(np.float64) / 65535.0
red = (linear[..., 0] - linear[..., 2] / WARMEST_GROUND) / (1.0 - LIGHTS[2] / WARMEST_GROUND)
lights = np.clip(red, 0.0, None)[..., None] * LIGHTS * brightness
render.save(lights, out)
lit = lights[..., 0] > 0
print(f"{out}: lights in {lit.mean():.1%} of the texels, mean red {lights[..., 0].mean():.4f}, brightest {lights[..., 0].max():.3f}")
