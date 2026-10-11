# Realistic Planets: sources

The scripts that make the Realistic Planets mod's files from public data. The mod's own
[README](../../mods/environment/realistic-planets/README.md) says what each step does and why, and
the note [`neptune-voyager-map.pdf`](../../mods/environment/realistic-planets/neptune-voyager-map.pdf)
describes Neptune's map in detail.

## What you need

- Python 3 with numpy and scipy, for example in a virtual environment:

  ```bash
  python3 -m venv venv && venv/bin/pip install numpy scipy
  ```

  Then put `venv/bin` first on your `PATH`, or run the scripts with `venv/bin/python3`.
- ImageMagick 7 (`magick`).
- `sltool` from OpenReliant, for the spheres.
- [Tectonic](https://tectonic-typesetting.github.io), for the note. It fetches the LaTeX packages it
  needs the first time it runs.

## Making the mod's files

Run each script from its own folder, in this order:

1. `neptune/build.sh` downloads Neptune's Voyager frames and Karkoschka's spectrum, about 70 MB,
   into `neptune/data`, and makes the texture, `realistic_planets_neptune.png`, in the mod's
   folder. It takes a few minutes.
2. `jupiter/build.sh` downloads Cassini's map, Hubble's OPAL maps and Karkoschka's spectrum, about
   93 MB, into `jupiter/data`, and makes `realistic_planets_jupiter.png`. It takes a few seconds.
3. `build.sh` builds the spheres with `sphere.py` and `sltool shp from-obj`, and the thumbnail,
   `mod.png`, with `render.py`. Set `SLTOOL` if `sltool` isn't on your `PATH`.
4. `paper/build.sh` makes the note's figures with `paper/figures.py` and typesets
   `paper/neptune.tex` into `neptune-voyager-map.pdf` in the mod's folder. `figures.py` also prints
   every number the note quotes, so that a new build can be checked against the text.

## The files

| File | What it does |
|---|---|
| `sphere.py` | Writes a sphere for a planet as an OBJ file, with an equirectangular map, flattened if asked |
| `render.py` | Draws a planet from its texture, for the thumbnail and the note's figures |
| `build.sh` | Builds the spheres and the thumbnail |
| `download.py` | Downloads files once each, for the bodies' fetch scripts |
| `truecolour.py` | Reads Karkoschka's spectra, and turns a reflectance spectrum into sRGB |
| `neptune/frames.json` | The Voyager frames used, with their geometry from OPUS and their download links |
| `neptune/fetch.py` | Downloads the frames and the spectrum |
| `neptune/fit.py` | Fits each frame's pointing; writes `fits.json`, and each frame's twist curve to `twists.json` |
| `neptune/blemishes.py` | Finds the camera's fixed blemishes; writes `pattern.npy` |
| `neptune/mosaic.py` | Mosaics the frames into `maps`, with the photometric self-calibration |
| `neptune/compose.py` | Composes the texture from the mosaics and the spectrum |
| `neptune/nepgeo.py` | Neptune's geometry, the frames' projection and photometry, shared by the scripts |
| `neptune/geomed.py` | Reads the Voyager GEOMED images |
| `jupiter/fetch.py` | Downloads Cassini's map, Hubble's OPAL maps and the spectrum |
| `jupiter/compose.py` | Calibrates Cassini's map with OPAL's and composes the texture |
| `paper/neptune.tex` | The note |
| `paper/figures.py` | The note's figures and numbers |

`fits.json` and `twists.json` are kept in the repository as a record of the fitted pointing. The
downloads, the mosaics and the note's figures aren't: the scripts make them again.
