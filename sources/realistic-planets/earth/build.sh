#!/bin/sh
# Makes Earth's texture from NASA's Blue Marble and the haze GOES-18 sees, and prints its limb's
# exponents from GOES-18's and GOES-19's pictures, as the mod's README.md describes. Run it from this
# folder, with Python 3, numpy, h5py and ImageMagick 7. It downloads about 730 MB into data.
set -eu
python3 fetch.py data
python3 limb.py data
# For the game: a mean luminance of 0.22, the same share of Earth's true brightness as Jupiter's 0.3
# is of Jupiter's, and the game's key light's blue of 0.8 divided out.
python3 compose.py data ../../../mods/environment/realistic-planets/realistic_planets_earth.png 4096 0.22 0.8
