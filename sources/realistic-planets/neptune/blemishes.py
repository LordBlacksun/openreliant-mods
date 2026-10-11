"""Finds the narrow-angle camera's fixed blemishes: faint rings that stay at the same pixels in every
frame, while Neptune's clouds don't. Each frame's fine detail on the disk, its band-passed brightness
over the local mean, is averaged in camera pixels over every frame; what is fixed adds up, and the
rest averages out. The mosaic divides each frame by this pattern within the rings it lists.

    python3 blemishes.py data frames.json pattern.npy
"""
import json
import sys

import numpy as np
from scipy import ndimage

import geomed
import nepgeo

data, listing, out = sys.argv[1], sys.argv[2], sys.argv[3]
total = np.zeros((1000, 1000))
count = np.zeros((1000, 1000))
for frame in json.load(open(listing))['frames']:
    name = frame['name']
    img, _ = geomed.image(f"{data}/{name}_GEOMED.IMG", f"{data}/{name}_GEOMED.LBL")
    med = ndimage.median_filter(img, size=3)
    clean = np.where(np.abs(img - med) > 0.02, med, img)
    disk = ndimage.binary_erosion((clean > 0.1) & (nepgeo.frame_mask(img) > 0), iterations=15)
    smooth = ndimage.gaussian_filter(clean, 10)
    band = (ndimage.gaussian_filter(clean, 1.5) - smooth) / np.maximum(smooth, 0.02)
    total += np.where(disk, band, 0)
    count += disk
pattern = np.where(count >= 8, total / np.maximum(count, 1), 0).astype(np.float32)
np.save(out, pattern)
print(f"averaged over {int(count.max())} frames at most")
