#!/bin/sh
# Makes Neptune's texture from Voyager 2's frames, and fits its haze beyond the disk to Voyager's
# frames at high phase, printing the numbers for neptune.glsl, as README.md describes. Run it from
# this folder, with Python 3, numpy, scipy and ImageMagick 7. It downloads about 150 MB into data,
# and writes its working files into fits.json, twists.json, pattern.npy and maps.
set -eu
data=data
epoch=1989-08-20T08:00:00
out=../../../mods/environment/realistic-planets/realistic_planets_neptune.png
mkdir -p maps
python3 fetch.py frames.json haze.json "$data"
python3 fit.py "$data" frames.json fits.json twists.json
python3 blemishes.py "$data" frames.json pattern.npy
python3 mosaic.py "$data" frames.json fits.json pattern.npy luminance "$epoch" 0.1 maps/luminance.npz
for filter in Orange Green Blue; do
    python3 mosaic.py "$data" frames.json fits.json pattern.npy "$filter" "$epoch" 0.25 "maps/$filter.npz"
done
# Contrast enhanced three times.
python3 compose.py maps "$data/1993.tab" "$out" 3
# The haze: compose.py writes data/colour.json, which turns its I/F into the texture's colours.
python3 haze.py "$data" haze.json
