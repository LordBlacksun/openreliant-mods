#!/bin/sh
# Makes Saturn's textures, the planet's from Hubble's calibrated maps and the ring's from Voyager 2's
# profiles and Cassini's colours, and fits its haze to Cassini's frames, printing the numbers for
# saturn.glsl, as the mod's README.md describes. Run it from this folder, with Python 3, numpy, scipy
# and ImageMagick 7. It downloads about 220 MB into data.
set -eu
mod=../../../mods/environment/realistic-planets
python3 fetch.py haze.json data
# For the game: Saturn's contrast stretched threefold, as the other planets' are, a mean luminance of
# 0.22, the same share of its true brightness as Jupiter's 0.3 is of Jupiter's, and the game's key
# light's blue of 0.8 divided out.
python3 compose.py data data/1993.tab "$mod/realistic_planets_saturn.png" 3 0.22 0.8
# The ring, its B ring at its brightest as bright as the planet's equatorial zone.
python3 rings.py data "$mod/realistic_planets_saturn.png" "$mod/realistic_planets_saturn_rings.png" 0.8
# The ring's optical depth for saturn.glsl, which shades the planet by the ring.
python3 ringdepth.py "$mod/realistic_planets_saturn_rings.png" 128
# The haze: compose.py writes data/colour.json, which turns its I/F into the texture's colours.
python3 haze.py data haze.json
