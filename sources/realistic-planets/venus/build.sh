#!/bin/sh
# Makes Venus's texture from Akatsuki's ultraviolet maps and Venus's albedos, and measures its limb
# from Venus Express's pictures, as the mod's README.md describes. Run it from this folder, with Python
# 3, numpy, scipy, h5py and ImageMagick 7. It downloads about 270 MB into data.
set -eu
python3 fetch.py data
# For the game: the ultraviolet markings four times as strong as the eye would see them, a mean
# luminance of 0.41, and the game's key light's blue of 0.8 divided out. Venus's geometric albedo has
# 1.36 times the luminance of Jupiter's, and both darken toward the limb about as a plain ball does,
# so its texture is 1.36 times as bright as Jupiter's 0.3.
python3 compose.py data ../../../mods/environment/realistic-planets/realistic_planets_venus.png 4 0.41 0.8
# The limb's exponents, for planets.luau.
python3 limb.py data
