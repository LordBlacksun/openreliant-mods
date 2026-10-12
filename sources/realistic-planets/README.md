# Realistic Planets: sources

The scripts that make the Realistic Planets mod's files from public data. The mod's own
[README](../../mods/environment/realistic-planets/README.md) says what each step does and why, and
the note [`neptune-voyager-map.pdf`](../../mods/environment/realistic-planets/neptune-voyager-map.pdf)
describes Neptune's map in detail.

## What you need

- Python 3 with numpy and scipy, and h5py for Venus and Earth, for example in a virtual environment:

  ```bash
  python3 -m venv venv && venv/bin/pip install numpy scipy h5py
  ```

  Then put `venv/bin` first on your `PATH`, or run the scripts with `venv/bin/python3`.
- ImageMagick 7 (`magick`).
- `sltool` from OpenReliant, for the spheres.
- [Tectonic](https://tectonic-typesetting.github.io), for the note. It fetches the LaTeX packages it
  needs the first time it runs.

## Making the mod's files

Run each script from its own folder, in this order:

1. `neptune/build.sh` downloads Neptune's Voyager frames and Karkoschka's spectrum, about 80 MB,
   into `neptune/data`, and makes the texture, `realistic_planets_neptune.png`, in the mod's folder.
2. `jupiter/build.sh` downloads Cassini's map, Hubble's OPAL maps and Karkoschka's spectrum, about
   93 MB, into `jupiter/data`, and makes `realistic_planets_jupiter.png`. It takes a few seconds.
3. `uranus/build.sh` downloads Hubble's OPAL maps of Uranus and Karkoschka's spectrum, about 3 MB,
   into `uranus/data`, and makes `realistic_planets_uranus.png`.
4. `saturn/build.sh` downloads Cassini's global maps of Saturn, Hubble's OPAL maps, Karkoschka's
   spectrum, Voyager 2's profiles of the rings and Cassini's mosaic across them, about 190 MB, into
   `saturn/data`, makes `realistic_planets_saturn.png` and the ring's,
   `realistic_planets_saturn_rings.png`, and prints the ring's optical depth for `saturn.glsl`. It
   takes under a minute.
5. `venus/build.sh` downloads Akatsuki's ultraviolet maps and Venus Express's pictures, about 270 MB,
   into `venus/data`, makes `realistic_planets_venus.png`, and prints the limb's exponents for
   `planets.luau`. It takes about a minute.
6. `titan/build.sh` downloads Cassini's frames of Titan, Cassini's map of its surface and
   Karkoschka's spectrum, about 60 MB, into `titan/data`, makes `realistic_planets_titan.png`, and
   prints the limb's exponents for `planets.luau`. It takes about ten seconds.
7. `moons/build.sh` downloads the USGS's maps of Io, Europa, Ganymede, Callisto and Triton and
   Voyager's colour frames of them, about 1.4 GB, into `moons/data`, fits the frames' pointing into
   `moons/fits.json`, makes `realistic_planets_io.png`, `realistic_planets_europa.png`,
   `realistic_planets_ganymede.png`, `realistic_planets_callisto.png` and
   `realistic_planets_triton.png`, and prints their limbs' exponents for `planets.luau`. The fit
   takes about 50 minutes.
8. `earth/build.sh` downloads NASA's Blue Marble and Black Marble and GOES-18's and GOES-19's
   pictures, about 740 MB, into `earth/data`, prints the limb's exponents for `planets.luau`, and
   makes `realistic_planets_earth.png` and its city lights, `realistic_planets_earth_emissive.png`.
   It takes about a minute.
9. `build.sh` builds the spheres, Saturn's with its ring, with `sphere.py` and `sltool shp
   from-obj`, and the thumbnail, `mod.png`, with `render.py`. Set `SLTOOL` if `sltool` isn't on your
   `PATH`.
10. `paper/build.sh` makes the note's figures with `paper/figures.py` and typesets
   `paper/neptune.tex` into `neptune-voyager-map.pdf` in the mod's folder. `figures.py` also prints
   every number the note quotes, so that a new build can be checked against the text.

## The files

| File | What it does |
|---|---|
| `sphere.py` | Writes a sphere for a planet as an OBJ file, with an equirectangular map, flattened, with a ring or off the model's origin if asked |
| `render.py` | Draws a planet from its texture, and its ring, for the thumbnail and the note's figures |
| `build.sh` | Builds the spheres and the thumbnail |
| `download.py` | Downloads files once each, and reads the download links of the frames a listing names, for the bodies' fetch scripts |
| `fits.py` | Reads the image of a FITS file, as Hubble's OPAL maps hold it |
| `truecolour.py` | Reads Karkoschka's spectra, turns a reflectance spectrum into sRGB, bends a spectrum through filters, and finds the wavelength each channel stands for |
| `minnaert.py` | Fits Minnaert's law with each band of latitude given its own brightness, for Venus and Titan |
| `globe.py` | Points from a body's centre toward a latitude and longitude, takes the area-weighted mean over its global map, and fits a circle to its disk's edge in a frame, for the bodies' scripts |
| `voyager.py` | Reads Voyager's GEOMED frames, works out a body's geometry as a frame sees it, and fits a frame's pointing to the sunlit limb, for Neptune, Jupiter's moons and Triton |
| `cassini.py` | Reads Cassini's calibrated frames, works out their geometry and fits a disk to its lit limb, for Titan's and Saturn's scripts |
| `neptune/frames.json` | The Voyager frames used for the texture, with their geometry from OPUS and their download links |
| `neptune/fetch.py` | Downloads the frames and the spectrum |
| `neptune/fit.py` | Fits each frame's pointing; writes `fits.json`, and each frame's twist curve to `twists.json` |
| `neptune/blemishes.py` | Finds the camera's fixed blemishes; writes `pattern.npy` |
| `neptune/mosaic.py` | Mosaics the frames into `maps`, with the photometric self-calibration |
| `neptune/compose.py` | Composes the texture from the mosaics and the spectrum |
| `neptune/nepgeo.py` | Neptune's shape, the camera's blemishes, Neptune's winds, and the twist found from its bands, shared by the scripts |
| `jupiter/fetch.py` | Downloads Cassini's map, Hubble's OPAL maps and the spectrum |
| `jupiter/compose.py` | Calibrates Cassini's map with OPAL's and composes the texture |
| `uranus/fetch.py` | Downloads Hubble's OPAL maps of Uranus and the spectrum |
| `uranus/compose.py` | Composes the texture from OPAL's maps and the spectrum |
| `saturn/fetch.py` | Downloads Cassini's and Hubble's maps, the spectrum, Voyager's ring profiles and Cassini's mosaic of the rings |
| `saturn/compose.py` | Composes the planet's texture from Cassini's maps, calibrated with Hubble's, and the spectrum |
| `saturn/rings.py` | Composes the ring's texture from Voyager's profiles and Cassini's mosaic |
| `saturn/ringdepth.py` | Prints the ring's optical depth for `saturn.glsl`, from the ring's texture |
| `venus/fetch.py` | Downloads Akatsuki's ultraviolet maps and Venus Express's pictures with their geometry |
| `venus/compose.py` | Composes the texture from Akatsuki's maps and Venus's albedos |
| `venus/limb.py` | Measures the limb's exponents from Venus Express's pictures |
| `venus/photometry.py` | Venus's spectrum, shared by `compose.py` and `limb.py` |
| `titan/frames.json` | The Cassini frames used for the texture, with their geometry from OPUS and the volume's index, and their download links |
| `titan/fetch.py` | Downloads the frames, the map of the surface and the spectrum |
| `titan/compose.py` | Fits the haze's profiles and the limb's exponents to the frames, and composes the texture with the map of the surface and the spectrum |
| `screenshots/titan.png` | The picture on the mod's page after its thumbnail: Titan in OpenReliant's mission 25, from 1.1 million units, 3.8 of its radii, at 30, 100, 150 and 165 degrees of phase, with the bloom and without the flight display, four views of 1920 by 1080 halved into one |
| `moons/frames.json` | The Voyager frames used: for Jupiter's moons one colour set for each 20 degrees of each moon's longitude, and for Triton every colour set, with their geometry from OPUS and their download links |
| `moons/fetch.py` | Downloads the frames and the USGS's maps |
| `moons/fit.py` | Fits each frame's pointing against its moon's map, and its limb darkening; writes `fits.json` |
| `moons/compose.py` | Composes a moon's texture from its map and the frames' colour |
| `moons/moons.py` | The moons' maps, shapes and frames, and the guess for Triton's unseen north, shared by `fit.py` and `compose.py` |
| `earth/fetch.py` | Downloads the Blue Marble, the Black Marble and the GOES pictures |
| `earth/goes.py` | Reads the GOES pictures onto latitude and longitude, with each place's angles of view and light, shared by `limb.py` and `compose.py` |
| `earth/limb.py` | Measures the limb's exponents from the two satellites' pictures of the same moment |
| `earth/compose.py` | Composes the texture from the Blue Marble, with the haze GOES-18 sees added back |
| `earth/nightlights.py` | Makes the city lights, the texture's emissive map, from the Black Marble |
| `paper/neptune.tex` | The note |
| `paper/figures.py` | The note's figures and numbers |

`neptune/fits.json`, `neptune/twists.json` and `moons/fits.json` are kept in the repository as a
record of the fitted pointing. The downloads, the mosaics and the note's figures aren't: the scripts
make them again.
