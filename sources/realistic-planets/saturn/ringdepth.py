"""Prints the ring's optical depth for `saturn.glsl`, which shades Saturn by its ring, as a GLSL array
of `bins` values evenly spaced from the ring's inner edge to its outer, from the ring's texture.

    python3 ringdepth.py realistic_planets_saturn_rings.png 128

The texture's alpha is the share of the light the ring stops seen face on, 1 - exp(-tau), the same
in every row. Each bin is the mean of the light its texels let through, as an optical depth: the
ring's shadow is the mean of the light through each part of it.
"""
import subprocess
import sys

import numpy as np

texture, bins = sys.argv[1], int(sys.argv[2])

# The least share of the light that a texel or a bin lets through, so that the depth stays finite.
LEAST = 1e-4

width, height = map(int, subprocess.run(['magick', 'identify', '-format', '%w %h', texture], capture_output=True, text=True,
                                         check=True).stdout.split())
raw = subprocess.run(['magick', texture, '-depth', '8', 'rgba:-'], capture_output=True, check=True).stdout
alpha = np.frombuffer(raw, np.uint8).reshape(height, width, 4)[height // 2, :, 3] / 255.0
through = np.clip(1.0 - alpha, LEAST, 1.0).reshape(bins, -1).mean(axis=1)
depth = -np.log(np.clip(through, LEAST, 1.0))
rows = [', '.join(repr(round(float(value), 3)) for value in depth[at:at + 16]) for at in range(0, bins, 16)]
print('const float saturnRingTau[saturnRingBins] = float[](\n    ' + ',\n    '.join(rows) + '\n);')
