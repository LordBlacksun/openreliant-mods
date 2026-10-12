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
spheres titan titan 288141 288141
# Io's near level is uneven, 270,744 to 273,753 units from its middle; its sphere takes their median.
spheres io io 270949 288141
# Europa's far level and far model are larger than its near level.
spheres europa europa 288141 331938
# Ganymede's far model is 50 times smaller than its detailed one, as the game's is.
spheres ganymede grany 288141 5763
spheres callisto calist 1280625 1280625
spheres triton triton 288141 288141

# Earth's model has one level, and its sphere stands 1.25 million units from the model's origin, as
# the game's does, centred where `sltool shp obj` puts the middle of the game's sphere. The mod makes
# Earth a planet, so the engine moves the sphere back to stand on its origin, as it does every
# planet's.
python3 sphere.py "$work/earth.obj" --radius 1048542 --centre -752661.5 5579.5 -993744.7 --texture realistic_planets_earth \
    --name earth
"$sltool" shp from-obj "$work/earth.obj" "$mod/earth.shp"

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

# The thumbnail: the planets in a row, in their order out from the sun, and their moons below them in
# the same order. Venus from 10 degrees north, facing the bright clouds north of its equator, Earth
# facing Africa and Europe, Jupiter facing its Great Red Spot, Saturn and its ring from 25 degrees
# north, Uranus from the north it shows now and Neptune facing its Great Dark Spot; then Jupiter's
# moons from the inside out, Io facing Pele and Loki, Europa its trailing side, Ganymede facing
# Galileo Regio and Callisto facing Valhalla, Titan facing Xanadu and Triton from 30 degrees south,
# facing the ground Voyager 2 saw best. Each is lit from the upper left, in white light, as if
# the sun stood 10 degrees above the viewer and 15 to the left, so that its night side just begins at
# its lower right edge, and its limb shows as the mod draws it: each channel with the exponent
# `planets.luau` gives it, held at its least cosine. Saturn's sun stands 27 degrees north, the most it
# does, and 20 degrees to the left, so that its night side begins at its right edge, where its ring
# doesn't hide it, and its shadow falls on the ring behind it, as the ring's shadow falls on its
# south, as the game draws them. They're flattened as their spheres are, the planets 90 pixels across
# and the moons 72. Each is drawn at four times its size and scaled down, so that the texture doesn't
# alias.
python3 render.py "$mod/realistic_planets_venus.png" "$work/venus.png" --size 360 --lat 10 --lon 45 \
    --sun-lat 20 --sun-lon 30 --k 1.070 1.077 0.982 --least 0.25
python3 render.py "$mod/realistic_planets_earth.png" "$work/earth.png" --size 360 --lat 10 --lon 15 \
    --sun-lat 20 --sun-lon 0 --k 0.871 0.815 0.750 --least 0.25
python3 render.py "$mod/realistic_planets_jupiter.png" "$work/jupiter.png" --size 360 --lat -15 --lon -46 \
    --sun-lat -5 --sun-lon -61 --k 0.988 0.965 0.905 --least 0.25 --polar 0.9351
python3 render.py "$mod/realistic_planets_saturn.png" "$work/saturn.png" --size 560 --aspect 1.536 --extent 1.556 \
    --lat 25 --lon 30 --sun-lat 27 --sun-lon 10 --k 0.770 0.697 0.540 --least 0.25 --polar 0.9020 \
    --ring "$mod/realistic_planets_saturn_rings.png" 1.2279 2.3396
python3 render.py "$mod/realistic_planets_uranus.png" "$work/uranus.png" --size 360 --lat 35 --lon 0 \
    --sun-lat 45 --sun-lon -15 --k 0.702 0.805 0.850 --least 0.25 --polar 0.9771
python3 render.py "$mod/realistic_planets_neptune.png" "$work/neptune.png" --size 360 --lat -25 --lon 37 \
    --sun-lat -15 --sun-lon 22 --k 0.680 0.712 0.768 --least 0.25
python3 render.py "$mod/realistic_planets_io.png" "$work/io.png" --size 288 --lat 5 --lon 100 \
    --sun-lat 15 --sun-lon 85 --k 0.685 0.688 0.697 --least 0.2
python3 render.py "$mod/realistic_planets_europa.png" "$work/europa.png" --size 288 --lat 5 --lon 90 \
    --sun-lat 15 --sun-lon 75 --k 0.669 0.670 0.663 --least 0.2
python3 render.py "$mod/realistic_planets_ganymede.png" "$work/ganymede.png" --size 288 --lat 10 --lon -160 \
    --sun-lat 20 --sun-lon -175 --k 0.580 0.561 0.539 --least 0.2
python3 render.py "$mod/realistic_planets_callisto.png" "$work/callisto.png" --size 288 --lat 15 --lon -56 \
    --sun-lat 25 --sun-lon -71 --k 0.578 0.563 0.532 --least 0.2
python3 render.py "$mod/realistic_planets_titan.png" "$work/titan.png" --size 288 --lat 15 --lon -100 \
    --sun-lat 25 --sun-lon -115 --k 0.877 0.892 0.876 --least 0.25
python3 render.py "$mod/realistic_planets_triton.png" "$work/triton.png" --size 288 --lat -30 --lon 0 \
    --sun-lat -20 --sun-lon -15 --k 0.741 0.744 0.750 --least 0.2
magick \( "$work/venus.png" "$work/earth.png" "$work/jupiter.png" -colorspace RGB -resize 90x90 -colorspace sRGB \
    -background black -gravity center -extent 97x140 \) \
    \( "$work/saturn.png" -colorspace RGB -resize 215x140 -colorspace sRGB -background black -gravity center -extent 215x140 \) \
    \( "$work/uranus.png" "$work/neptune.png" -colorspace RGB -resize 90x90 -colorspace sRGB -background black \
    -gravity center -extent 97x140 \) +append \
    \( "$work/io.png" "$work/europa.png" "$work/ganymede.png" "$work/callisto.png" "$work/titan.png" "$work/triton.png" \
    -colorspace RGB -resize 72x72 -colorspace sRGB -background black -gravity center -extent 116x140 +append \
    -extent 700x140 \) -append +repage -define png:exclude-chunks=date,time "$mod/mod.png"
