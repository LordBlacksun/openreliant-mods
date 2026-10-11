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
# and the far model.
spheres() {
    python3 sphere.py "$work/$1_hi.obj" --radius "$2" --texture "realistic_planets_$1" --name "$1"
    python3 sphere.py "$work/$1_lo.obj" --radius "$3" --texture "realistic_planets_$1" --name "$1" --columns 64 --rows 32
    "$sltool" shp from-obj "$work/$1_hi.obj" "$mod/$1_hi_1.shp"
    "$sltool" shp from-obj "$work/$1_lo.obj" "$mod/$1_lo_1.shp"
}
spheres neptune 1280625 1024500

# The thumbnail: Neptune from 25 degrees south facing the Great Dark Spot, the second dark spot and
# the side away from both, lit as the game lights it. Each view is drawn at four times its size and
# scaled down, so that the texture doesn't alias.
for lon in 37 316 177; do
    python3 render.py "$mod/realistic_planets_neptune.png" "$work/$lon.png" --size 880 --lat -25 --lon "$lon" \
        --sun-lat -26 --sun-lon $((lon + 15)) --light 1 1 0.8
    magick "$work/$lon.png" -colorspace RGB -resize 220x220 -colorspace sRGB "$work/$lon.png"
done
magick "$work/37.png" "$work/316.png" "$work/177.png" -background black -gravity center -extent 233x280 +append \
    -extent 700x280 +repage -define png:exclude-chunks=date,time "$mod/mod.png"
