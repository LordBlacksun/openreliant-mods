#!/bin/sh
# Makes Jupiter's texture from Cassini's map and Hubble's calibrated maps, as the mod's README.md
# describes. Run it from this folder, with Python 3, numpy, scipy and ImageMagick 7. It downloads
# about 93 MB into data.
set -eu
python3 fetch.py data
# For the game: Jupiter's contrast stretched threefold, as Neptune's is, a mean luminance of 0.3, and
# the game's key light's blue of 0.8 divided out.
python3 compose.py data data/1993.tab ../../../mods/environment/realistic-planets/realistic_planets_jupiter.png 3 0.3 0.8
