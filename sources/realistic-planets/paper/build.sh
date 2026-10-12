#!/bin/sh
# Makes the figures of the note on Neptune's map and the note itself, after ../neptune/build.sh. Run
# it from this folder, with the same Python and ImageMagick 7, and Tectonic, which typesets the
# LaTeX.
set -eu
neptune=../neptune
mod=../../../mods/environment/realistic-planets
mkdir -p work
# The map in true colour, without the contrast stretch.
python3 "$neptune/compose.py" "$neptune/maps" "$neptune/data/1993.tab" work/true-colour.png 1
python3 figures.py "$neptune" work/true-colour.png "$mod/realistic_planets_neptune.png" figures
tectonic --outdir work neptune.tex
cp work/neptune.pdf "$mod/neptune-voyager-map.pdf"
