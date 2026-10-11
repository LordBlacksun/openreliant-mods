#!/bin/sh
# Builds the mod's spheres with sphere.py and sltool, and its thumbnail with render.py, once each
# body's build.sh has made its textures. Run it from this folder, with Python 3 and numpy,
# ImageMagick 7, and sltool on the PATH or named by SLTOOL.
set -eu
sltool=${SLTOOL:-sltool}
mod=../../mods/environment/realistic-planets
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# A body's two spheres, given its name, the name of the game's models of it, and the radii of the
# game's models: the detailed model's near level, and the far model. A flattened body's polar radii
# follow them.
spheres() {
    python3 sphere.py "$work/$1_hi.obj" --radius "$3" --polar "${5:-$3}" --texture "realistic_planets_$1" --name "$1"
    python3 sphere.py "$work/$1_lo.obj" --radius "$4" --polar "${6:-$4}" --texture "realistic_planets_$1" --name "$1" \
        --columns 64 --rows 32
    "$sltool" shp from-obj "$work/$1_hi.obj" "$mod/$2_hi_1.shp"
    "$sltool" shp from-obj "$work/$1_lo.obj" "$mod/$2_lo_1.shp"
}
spheres neptune neptune 1280625 1024500
# Jupiter's polar radius is 66,854 km to its equator's 71,492 (IAU).
spheres jupiter jupiter 1280625 1024500 1197545 958036
# Uranus's is 24,973 km to its equator's 25,559 (IAU); its far model is as large as its near one.
spheres uranus uranus 1280625 1280625 1251264 1251264
# Venus's far model is a little larger than its near one.
spheres venus venus1 1280625 1296633

# Saturn and its ring, at their real proportions: radii of 60,268 and 54,364 km (IAU), and the ring
# from 74,000 to 141,000 km, as its texture is. They're scaled so that the A ring's outer edge,
# 136,770 km out, falls where the original's ring ends, 4,640,000 units out, which is 33.93 units a
# km; the F ring then falls on the original's thin outer ring. The far model's planet is 0.988 of the
# detailed one's size, as the original's is, and its ring the same.
python3 sphere.py "$work/saturn_hi.obj" --radius 2044626 --polar 1844330 --texture realistic_planets_saturn --name saturn \
    --ring 2510492 4783505 --ring-texture realistic_planets_saturn_rings
python3 sphere.py "$work/saturn_lo.obj" --radius 2020365 --polar 1822445 --texture realistic_planets_saturn --name saturn \
    --columns 64 --rows 32 --ring 2510492 4783505 --ring-texture realistic_planets_saturn_rings --ring-segments 128
"$sltool" shp from-obj "$work/saturn_hi.obj" "$mod/saturn_hi_ring_2.shp"
"$sltool" shp from-obj "$work/saturn_lo.obj" "$mod/saturn_lo_ring_1.shp"

# The thumbnail, the planets in their order out from the sun's far side: Neptune facing its Great Dark
# Spot, Uranus from the north it shows now, Saturn and its ring from 25 degrees north, Jupiter facing
# its Great Red Spot, and Venus from 10 degrees north, facing the bright clouds north of its equator,
# lit as the game lights them, flattened as their spheres are, each 104 pixels across. Each is drawn
# at four times its size and scaled down, so that the texture doesn't alias.
python3 render.py "$mod/realistic_planets_neptune.png" "$work/neptune.png" --size 416 --lat -25 --lon 37 \
    --sun-lat -26 --sun-lon 52 --light 1 1 0.8
python3 render.py "$mod/realistic_planets_uranus.png" "$work/uranus.png" --size 416 --lat 35 --lon 0 \
    --sun-lat 34 --sun-lon 15 --k 0.8 --light 1 1 0.8 --polar 0.9771
python3 render.py "$mod/realistic_planets_saturn.png" "$work/saturn.png" --size 940 --aspect 1.075 --extent 2.258 \
    --lat 25 --lon 30 --sun-lat 26 --sun-lon 50 --k 0.7 --light 1 1 0.8 --polar 0.9020 \
    --ring "$mod/realistic_planets_saturn_rings.png" 1.2279 2.3396
python3 render.py "$mod/realistic_planets_jupiter.png" "$work/jupiter.png" --size 416 --lat -15 --lon -46 \
    --sun-lat -16 --sun-lon -31 --k 0.97 --light 1 1 0.8 --polar 0.9351
python3 render.py "$mod/realistic_planets_venus.png" "$work/venus.png" --size 416 --lat 10 --lon 45 \
    --sun-lat 9 --sun-lon 60 --k 1.08 --light 1 1 0.8
magick \( "$work/neptune.png" "$work/uranus.png" -colorspace RGB -resize 104x104 -colorspace sRGB \
    -background black -gravity center -extent 112x280 \) \
    \( "$work/saturn.png" -colorspace RGB -resize 252x235 -colorspace sRGB -background black -gravity center -extent 252x280 \) \
    \( "$work/jupiter.png" "$work/venus.png" -colorspace RGB -resize 104x104 -colorspace sRGB \
    -background black -gravity center -extent 112x280 \) \
    +append -background black -gravity center -extent 700x280 +repage -define png:exclude-chunks=date,time "$mod/mod.png"
