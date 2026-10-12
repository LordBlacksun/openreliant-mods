#!/bin/sh
# Makes Uranus's texture from Hubble's calibrated maps, as the mod's README.md describes. Run it from
# this folder, with Python 3, numpy, scipy and ImageMagick 7. It downloads about 3 MB into data.
set -eu
python3 fetch.py data
# For the game: Uranus's contrast stretched threefold, as Neptune's and Jupiter's are, and a mean
# luminance of 0.55, a little brighter than Neptune's 0.50 as the real planet is.
python3 compose.py data data/1993.tab ../../../mods/environment/realistic-planets/realistic_planets_uranus.png 3 0.55
