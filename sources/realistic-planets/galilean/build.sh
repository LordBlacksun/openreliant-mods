#!/bin/sh
# Makes the Galilean moons' textures from the USGS's maps and Voyager's colour frames, and prints their
# limbs' exponents, as the mod's README.md describes. Run it from this folder, with Python 3, numpy,
# scipy and ImageMagick 7. It downloads about 970 MB into data, and writes the frames' fitted pointing
# into fits.json.
set -eu
mod=../../../mods/environment/realistic-planets
python3 fetch.py frames.json data
python3 fit.py data frames.json fits.json
# For the game: Ganymede's texture 8192 wide, as mission 83 shows it from close by, and the others
# 4096; each moon's mean luminance, the same share of its true brightness as Jupiter's 0.3 is of
# Jupiter's; and the game's key light's blue of 0.8 divided out.
python3 compose.py data frames.json fits.json Io "$mod/realistic_planets_io.png" 4096 0.29 0.8
python3 compose.py data frames.json fits.json Europa "$mod/realistic_planets_europa.png" 4096 0.31 0.8
python3 compose.py data frames.json fits.json Ganymede "$mod/realistic_planets_ganymede.png" 8192 0.18 0.8
python3 compose.py data frames.json fits.json Callisto "$mod/realistic_planets_callisto.png" 4096 0.08 0.8
