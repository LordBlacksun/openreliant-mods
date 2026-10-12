#!/bin/sh
# Makes Titan's texture from Cassini's frames and map and Karkoschka's spectrum, prints its limb's
# exponents, and fits its haze beyond the disc to Cassini's frames at low and high phase, printing the
# numbers for titan.glsl, as the mod's README.md describes. Run it from this folder, with Python 3,
# numpy, scipy and ImageMagick 7. It downloads about 200 MB into data.
set -eu
python3 fetch.py frames.json haze.json data
# For the game: the surface shown at 0.15 of its contrast through the haze, a mean luminance of 0.12,
# the same share of Titan's true brightness as Jupiter's 0.3 is of Jupiter's, and the game's key
# light's blue of 0.8 divided out.
python3 compose.py data frames.json data/1993.tab ../../../mods/environment/realistic-planets/realistic_planets_titan.png 0.15 0.12 0.8
# The haze: compose.py writes data/colour.json, which turns its I/F into the texture's colours.
python3 haze.py data frames.json haze.json
