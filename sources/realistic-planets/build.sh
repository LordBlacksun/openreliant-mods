#!/bin/sh
# Builds the mod's spheres with sphere.py and sltool, and its thumbnail with render.py, once the
# textures are made (neptune/build.sh). Run it from this folder, with Python 3 and numpy,
# ImageMagick 7, and sltool on the PATH or named by SLTOOL.
set -eu
sltool=${SLTOOL:-sltool}
mod=../../mods/environment/realistic-planets
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# A body's two spheres, with the radii of the game's own models: the detailed model's near level,
# and the far model. A flattened body's polar radii follow them.
spheres() {
    python3 sphere.py "$work/$1_hi.obj" --radius "$2" --polar "${4:-$2}" --texture "realistic_planets_$1" --name "$1"
    python3 sphere.py "$work/$1_lo.obj" --radius "$3" --polar "${5:-$3}" --texture "realistic_planets_$1" --name "$1" \
        --columns 64 --rows 32
    "$sltool" shp from-obj "$work/$1_hi.obj" "$mod/$1_hi_1.shp"
    "$sltool" shp from-obj "$work/$1_lo.obj" "$mod/$1_lo_1.shp"
}
spheres neptune 1280625 1024500
# Jupiter's polar radius is 66,854 km to its equator's 71,492 (IAU).
spheres jupiter 1280625 1024500 1197545 958036
# Uranus's is 24,973 km to its equator's 25,559 (IAU); its far model is as large as its near one.
spheres uranus 1280625 1280625 1251264 1251264

# The thumbnail: Neptune facing its Great Dark Spot, Uranus from the north it shows now, and Jupiter
# facing its Great Red Spot, lit as the game lights them, Uranus and Jupiter flattened as their spheres
# are. Each is drawn at four times its size and scaled down, so that the texture doesn't alias.
python3 render.py "$mod/realistic_planets_neptune.png" "$work/neptune.png" --size 880 --lat -25 --lon 37 \
    --sun-lat -26 --sun-lon 52 --light 1 1 0.8
python3 render.py "$mod/realistic_planets_uranus.png" "$work/uranus.png" --size 880 --lat 35 --lon 0 \
    --sun-lat 34 --sun-lon 15 --k 0.8 --light 1 1 0.8 --polar 0.9771
python3 render.py "$mod/realistic_planets_jupiter.png" "$work/jupiter.png" --size 880 --lat -15 --lon -46 \
    --sun-lat -16 --sun-lon -31 --k 0.97 --light 1 1 0.8 --polar 0.9351
magick "$work/neptune.png" "$work/uranus.png" "$work/jupiter.png" -colorspace RGB -resize 220x220 -colorspace sRGB \
    -background black -gravity center -extent 233x280 +append -extent 700x280 +repage \
    -define png:exclude-chunks=date,time "$mod/mod.png"
