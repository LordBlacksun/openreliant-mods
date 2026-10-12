#!/bin/sh
# Makes Titan's texture from Cassini's frames and map and Karkoschka's spectrum, and prints its limb's
# exponents, as the mod's README.md describes. Run it from this folder, with Python 3, numpy, scipy
# and ImageMagick 7. It downloads about 60 MB into data.
set -eu
python3 fetch.py frames.json data
# For the game: the surface shown at 0.15 of its contrast through the haze, and a mean luminance of
# 0.12, the same share of Titan's true brightness as Jupiter's 0.3 is of Jupiter's.
python3 compose.py data frames.json data/1993.tab ../../../mods/environment/realistic-planets/realistic_planets_titan.png 0.15 0.12
