#!/bin/sh
# Makes Earth's texture from NASA's Blue Marble and the haze GOES-18 sees, and its city lights from
# NASA's Black Marble, and prints its limb's exponents from GOES-18's and GOES-19's pictures, as the
# mod's README.md describes. Run it from this folder, with Python 3, numpy, h5py and ImageMagick 7.
# It downloads about 740 MB into data.
set -eu
python3 fetch.py data
python3 limb.py data
# For the game: a mean luminance of 0.22, the same share of Earth's true brightness as Jupiter's 0.3
# is of Jupiter's.
python3 compose.py data ../../../mods/environment/realistic-planets/realistic_planets_earth.png 4096 0.22
# The city lights, at the texture's size and the Black Marble's brightness.
python3 nightlights.py data/BlackMarble_2016_3km.jpg ../../../mods/environment/realistic-planets/realistic_planets_earth_emissive.png 4096 1
