# Realistic Planets

Replaces StarLancer's planets and moons with round, finely divided spheres, mapped from real
spacecraft and telescope imagery. This file records how the mod is made and where every picture
comes from, so that anyone can check it or make it again. The scripts are in the collection's
[`sources/realistic-planets`](https://github.com/OpenReliant/openreliant-mods/tree/main/sources/realistic-planets)
folder.

**Status:** Neptune and Jupiter are done. The other bodies follow.

## The game's planets

Each body comes as a detailed model and a far one, as separate object types (`0x5F` to `0x6A` and
`0xC9` to `0xD3`), with 256x256 textures:

| Body | Detailed | Far | Texture |
|---|---|---|---|
| Neptune | `neptune_hi_1.shp` | `neptune_lo_1.shp` | `neptune_2` |
| Triton | `triton_hi_1.shp` | `triton_lo_1.shp` | `triton_4`, with polar caps `triton_top`, `triton_bot` |
| Uranus | `uranus_hi_1.shp` | `uranus_lo_1.shp` | `uranus_1` |
| Saturn and its ring | `saturn_hi_ring_2.shp` | `saturn_lo_ring_1.shp` | `saturn_2`, `saturn6` |
| Titan | `titan_hi_1.shp` | `titan_lo_1.shp` | `Titon_1` |
| Jupiter | `jupiter_hi_1.shp` | `jupiter_lo_1.shp` | `jupiter_1` |
| Europa | `europa_hi_1.shp` | `europa_lo_1.shp` | `europa_5` |
| Ganymede | `grany_hi_1.shp` | `grany_lo_1.shp` | |
| Io | `io_hi_1.shp` | `io_lo_1.shp` | `io_1`, `io_bot` |
| Callisto | `calist_hi_1.shp` | `calist_lo_1.shp` | |
| Venus | `venus1_hi_1.shp` | `venus1_lo_1.shp` | `venus_1`, `venus_top`, `venus_bot` |
| Earth | `earth.shp` | | |

What OpenReliant's source and `sltool` show about them:

- A detailed model has two levels of detail. Neptune's near level, a 720-triangle sphere with a
  radius of 1,280,625 units, draws within 25,000,000 units; its far level, 320 triangles with a
  radius of 1,024,500, draws beyond that, out to 2,500,000,000. The far model is a 320-triangle
  sphere of the far level's size.
- The engine moves each level to stand on the middle of its vertices and works out its normals
  again from its faces. It lights a planet with the scene's second key light alone, whose colour is
  (1, 1, 0.8), and takes the planet's radius from its last level.
- Neptune, Uranus, Jupiter and Venus have an atmosphere: a band that faces the camera and is added
  over the planet, sized by that radius. Neptune's and Uranus's band runs from 0.85 to 0.95 of the
  radius, inside the disk, so it hardly shows; Jupiter's and Venus's reach just past the edge, to
  1.005.
- The same four planets turn about their own Y by 0.0007 of a radian each tick. With 100 ticks a
  second, that's one turn every 90 seconds. Y points down in the game's frame, and a positive turn
  about it carries this mod's maps westward, while Neptune and Jupiter really turn eastward. A mod
  can't change the turn yet ([OpenReliant/openreliant#1083](https://github.com/OpenReliant/openreliant/issues/1083)).
- Each model carries an animation clip that never plays, so the spheres here leave it out.
- The two levels of Neptune's detailed model map the texture differently from each other, so
  nothing of the original layout is worth keeping.
- The views that come closest, from the missions' nav points and starts:

  | Body | Mission | Point | Distance from the centre, units |
  |---|---|---|---|
  | Titan | 251 | patrol_routesnapping2 | 0.82 million |
  | Ganymede | 83 | spawn_player5 | 1.05 million |
  | Titan | 25 | patrol_routewl | 1.22 million |
  | Neptune | 3 | Sci pat point 2 | 1.87 million, 0.59 million above the clouds |
  | Venus | 3 | patrol_route | 2.68 million |
  | Neptune | 4 | FinishedStorks | 3.13 million |

  From mission 3's point, Neptune spans about 86 degrees and fills the screen, so its map has to
  hold up at that size.

## The models

- Each body gets two spheres made by `sphere.py` and built with `sltool shp from-obj`: the detailed
  model, 128 by 64 segments (16,128 triangles) with the near level's radius, and the far model, 64
  by 32 (3,968 triangles) with the far model's radius.
- The texture is equirectangular: north at the top, longitude 0 in the middle column and east to
  the right. `sphere.py` writes the poles on Y, north at +Y, longitude 0 toward +Z and east toward
  +X. `sltool shp from-obj` turns an OBJ file half a turn about Z into the game's frame, where Y
  points down, so in the game north is at -Y, up on the screen while the planet isn't turned, and
  east at -X. Seen from outside, the map isn't mirrored: a labelled grid confirmed this in the
  game.
- The seam's and the poles' vertices are shared, and the texture coordinates go with each corner, so
  the normals the engine works out stay smooth across the seam, where split vertices would show a
  line.
- Jupiter is flattened, as the real planet is: its spheres' polar radius is 0.935 of their
  equator's, 66,854 km to 71,492 (IAU). Their rings stand at planetocentric latitudes, as Cassini's
  map has them; on a sphere both kinds of latitude agree.
- The textures are named `realistic_planets_<body>`, so the game's own stay for any other model that
  uses them.

## Neptune

The map is made from 34 calibrated Voyager 2 frames taken on 17 and 20 August 1989, with the colour
taken from a ground-based spectrum of Neptune. The note
[`neptune-voyager-map.pdf`](neptune-voyager-map.pdf) in this folder describes the method in detail,
with figures and references.

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| Voyager 2 imaging, through the [PDS Ring-Moon Systems Node](https://pds-rings.seti.org/) | Calibrated narrow-angle frames from the 1989 flyby | Public domain (NASA/JPL) | Yes |
| E. Karkoschka's spectra of the giant planets, through the [PDS Atmospheres Node](https://pds-atmospheres.nmsu.edu/) | Neptune's geometric albedo from 300 to 1000 nm, measured in July 1993 | NASA Planetary Data System | Yes, for the colour |
| [Hubble OPAL](https://archive.stsci.edu/hlsp/opal), 2015 | A real colour global map, 720x360, 2 pixels a degree | CC BY 4.0 | For the first test only |
| [Solar System Scope](https://www.solarsystemscope.com/textures/) | A 2048x1024 map | CC BY 4.0 | No: partly made up, and oversaturated, as its page says |
| "Neptune (1989-2025)", a Celestia add-on | Maps from Voyager and Hubble | None stated | No |
| [Björn Jónsson's mosaics](https://www.planetary.org/articles/08250839-best-ever-neptune-mosaics) (2014) | The best Voyager mosaics made so far | None stated | No, but the method here follows the same lines |

No ready-made true-colour map of Neptune is both sharp and free to share. Hubble resolves about
1000 km on Neptune; its map is real but soft, Hubble saw Neptune's north edge-on, so the map has no
data past about 55 degrees north and stripes down to about 30, and its composite of the F657N,
F547M and F467M filters reads green in the game. Up close, in mission 3, the game's own painted
texture showed more structure. So this map is made from Voyager 2's frames.

### The Voyager 2 frames

OPUS, the Ring-Moon Systems Node's search, lists 716 narrow-angle frames of Neptune from 14 to 25
August 1989. In the frames used, the phase angle is 15 degrees, the sub-spacecraft latitude -28.5
and the sub-solar latitude -23.2, so the south is seen well and the far north is seen edge-on or
not at all. The whole disk fits a frame from about 6.3 million km out, and the frames of 20 August
are among the last where it does.

- **Luminance:** 10 clear and green frames from 20 August, 62 to 70 km a pixel, all round the
  planet: C1124807, C1124950, C1125011, C1125424, C1123602, C1123656, C1124039, C1124304, C1124441
  and C1124452.
- **Colour:** 8 sets of orange, green and blue frames from 17 August, 97 to 109 km a pixel, also
  all round: C1116553, C1116615, C1116542; C1114843, C1114855, C1114837; C1116901, C1116923,
  C1116850; C1117327, C1117339, C1117321; C1117415, C1117427, C1117409; C1115735, C1115757,
  C1115724; C1116037, C1116059, C1116026; C1116225, C1116229, C1116223.

Each is the archive's GEOMED product: calibrated to I/F, the camera's distortion removed, 1000 by
1000 pixels of 7.842 microradians.

### Placing each frame

- OPUS gives each frame's range, sub-spacecraft point and sub-solar point. The cameras' pointing
  couldn't be found for Neptune: NAIF's Voyager 2 C-kernel holds the orientation of the
  spacecraft's body alone, not of the scan platform the cameras sit on. So each frame's pointing is
  fitted to the frame itself, with Neptune as an oblate spheroid of 24,764 by 24,341 km.
- **Centre and scale:** a first guess matches a lit, limb-darkened model disk to the image, but it
  is off by up to 26 pixels, where the model is weakest near the edge. The final fit uses the sunlit
  limb alone: along lines from the centre, the point where the brightness falls half way to the sky
  is found to a fraction of a pixel, and the model's edge is fitted through those points. The fits
  leave 0.4 to 0.8 pixels of scatter, and the scale comes out at 0.998 on average, a small, steady
  correction to the nominal pixel size.
- **Twist,** where north points in the frame: the disk's outline barely shows it, so it comes from
  the clouds. The frame is mapped onto latitude and longitude at twists half a degree apart, and
  Neptune's bands follow lines of latitude, so the right twist is the one where the brightness
  varies least along each latitude. The spread is measured with the median absolute deviation, so
  that single storms such as the Great Dark Spot don't dominate it. Single frames scatter by a few
  degrees, so each day's curves are summed, and a parabola through the lowest three points finds
  the minimum between the steps: -6.85 degrees on 17 August and -6.31 on 20 August. Resampling the
  frames gives a spread of 0.47 and 0.25 degrees, and small changes to the processing move the
  values by up to about a degree.

### The camera's blemishes

The first mosaics showed small dark rings. They stay at the same pixels in every frame while the
clouds move, so averaging every frame's fine detail in camera pixels brings them out. Five compact
rings are divided out of each frame with that averaged pattern. Masking them instead left holes
where only one frame saw a spot well. Single bad pixels are replaced by their neighbours' median.

### Photometry

Limb darkening comes out with Minnaert's law, I/F = B mu0^k mu^(k-1), where mu and mu0 are the
cosines of the viewing and lighting angles, fitted for each frame. k is about 0.68 in orange, 0.71
in green, 0.75 in clear and 0.77 in blue.

Minnaert's law is weakest at steep angles, and north of the equator every frame sees the clouds
steeply, so the first mosaics showed steps in brightness where one frame took over from another.
Where frames overlap, the same cloud is seen at different angles, so a gain for each frame and a
smooth correction in the viewing and lighting angles, shared by all frames, are fitted to the
overlaps' brightness ratios. Points that don't fit, such as clouds that moved otherwise than the
winds, are dropped. For the luminance frames, 900,000 sample pairs fit with a scatter of 2.2%, and
the steps disappear.

### Winds

Neptune's clouds move fast against the planet's rotation (System III): about 400 m/s westward at
the equator. Frames a few hours apart show the same cloud at longitudes up to about 50 degrees
apart. Each frame is moved to one moment, 08:00 UTC on 20 August, with the zonal wind profile of
Sromovsky and others (1993), U = -398 + 0.188 lat^2 - 0.000012 lat^4 m/s. Single features drift at
their own rates, such as the Great Dark Spot, so their places are close but not exact, as in every
Voyager mosaic.

### The mosaic

Each frame's albedo goes onto a grid of 0.1 degrees, 0.25 for the colour frames, weighted by how
squarely its spot was seen and lit, by its resolution, and by its distance from the frame's edge.
The weight is cubed, so the best view of each spot outweighs the others, and the seams stay soft
without averaging different moments into ghosts. The data covers 85% of the surface: all round the
planet up to 37 degrees north, and in places up to 47.

### Colour

Voyager's orange, green and blue filters sit at about 591, 566 and 479 nm. They miss the red end of
the spectrum, where Neptune's methane absorbs most and which sets much of its colour, so they can't
give true colour on their own. Instead:

- Karkoschka's spectrum of Neptune gives the mean colour. It's integrated with the CIE 1931
  observer, in Wyman, Sloan and Shirley's analytic fit, under a 5778 K blackbody standing in for
  sunlight, adapted to D65 white with the Bradford transform, into sRGB: (138, 182, 202), a pale,
  slightly greyish cyan blue, in line with Irwin and others' (2024) finding that Neptune is a pale
  greenish blue, not the deep blue of many published pictures.
- At each place, the spectrum is bent by the blue, green and orange mosaics' ratios to their means,
  through weights centred on the three filters, so the bands and storms keep their measured colour
  differences. The colour frames are three days older than the luminance frames, so the colour is
  smoothed over 2 degrees and the brightness comes from the luminance mosaic alone.
- As a check, the spectrum's ratios at the filters match Voyager's: blue to green is 1.267 in the
  spectrum and 1.242 in the frames. Orange to green is 0.862 and 0.786; the orange filter reaches
  into a methane band, and the map takes only each filter's variations from Voyager, so this
  doesn't change its colour.

### The far north

Past 32 degrees north every frame saw the clouds near its edge, and the data ends between 37 and 47
north. From 32 to 40 north the map blends into the southern hemisphere's bands at the same latitude,
averaged along each latitude over 45 degrees so that no cloud shows twice. It's a plausible guess,
not data.

### For the game

Two changes are made to the texture for the game alone:

- In true colour, Neptune's brightness varies by only a few per cent, which looks featureless on a
  game screen, so the texture stretches the brightness's differences from the mean threefold, as
  Voyager's published pictures of Neptune were stretched. The mean colour stays the same.
- The game lights a planet with a single light of colour (1, 1, 0.8), which its tone curve turns
  into a strong yellow cast, so the texture's blue is divided by 0.8.

### Sharper frames

Frames from 21 and 22 August, at 30 to 53 km a pixel, could give about twice the detail. They were
tried and left out: most show too little of the limb to fix their pointing, the camera's twist
appears to drift by several degrees after 20 August, and the clouds had changed shape within a day
or two, so the mosaic showed curved seams and features that didn't line up. Using them would take
the scan platform's pointing, or mosaics of frames taken close together in time, combined later.

## Jupiter

Jupiter's map is Cassini's global map from its flyby in December 2000, with its contrast measured
against Hubble's calibrated maps of January 2015 and its colour taken from Karkoschka's spectrum.

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| [Cassini's cylindrical map](https://science.nasa.gov/photojournal/cassinis-best-maps-of-jupiter-cylindrical-map) (PIA07782) | 36 narrow-angle frames of 11 and 12 December 2000, in filters at 451 and 750 nm, as one map of 0.1 degrees a pixel in planetocentric latitude | Public domain (NASA/JPL/Space Science Institute) | Yes |
| Cassini's polar maps (PIA07783 and PIA07784) | The same frames, as polar stereographic maps | Public domain | No: the same views, and no more of the poles |
| [Hubble OPAL](https://archive.stsci.edu/hlsp/opal), January 2015 | Calibrated maps at 395, 502 and 631 nm, in I/F, the limb darkening taken out by Minnaert's law | CC BY 4.0 | To measure Jupiter's contrast and limb darkening |
| E. Karkoschka's spectra, through the [PDS Atmospheres Node](https://pds-atmospheres.nmsu.edu/) | Jupiter's geometric albedo from 300 to 1000 nm, measured in July 1993 | NASA Planetary Data System | For the colour |

### The map

- Cassini's map covers every longitude from 88 degrees north to 82 south. Past that, Cassini saw
  nothing, and the map holds one flat colour. The last 3 degrees of data fade into their own mean
  colour, which fills the two small caps.
- The polar maps line up with the cylindrical one to a correlation of 0.99 where they overlap, so
  they hold the same views, and they stop at the same latitudes. They add nothing, and aren't used.
- The texture keeps the cylindrical map's own longitudes.

### Contrast

Cassini's published map has its contrast stretched, as pictures of Jupiter usually do. OPAL's maps
are calibrated, so they show Jupiter's own. Measured as the ratio between the 10th and the 90th
percentiles of the brightness, from 60 degrees south to 60 north, Jupiter's contrast is 1.70 at
395 nm, 1.45 at 502 nm and 1.25 at 631 nm. At each channel's wavelength for Jupiter's spectrum:

| Channel | Wavelength | Jupiter | Cassini's published map |
|---|---|---|---|
| Red | 602 nm | 1.29 | 2.24 |
| Green | 541 nm | 1.38 | 3.08 |
| Blue | 454 nm | 1.56 | 4.39 |

On the logarithm of the brightness, Cassini's map has about 3.3 times Jupiter's contrast. The
texture brings each channel to Jupiter's own contrast, then stretches it threefold for the game, as
Neptune's: close to Cassini's look, with each channel in Jupiter's own proportions.

### Colour and brightness

- Cassini made its colours from two filters, so the map keeps its own variations, but its mean
  colour is set to Karkoschka's spectrum of Jupiter, through the CIE 1931 observer as for Neptune:
  sRGB (189, 189, 172), a pale cream.
- OPAL's mean normal albedo is 1.53 times the spectrum's geometric albedo, which puts Jupiter's
  mean luminance at about 0.77. In the game's lighting that's near white, and the bloom makes it
  glow. So the texture's mean luminance is set to 0.3, a choice for the game, as the stretch is.
- As for Neptune, the texture's blue is divided by 0.8 for the game's light.

Jupiter turns the wrong way in the game too, until a mod can set a planet's spin
([OpenReliant/openreliant#1083](https://github.com/OpenReliant/openreliant/issues/1083)).

## The limb

A planet's haze makes its sunlit limb brighter than a plain ball's would be. The mod's player
script, `planets.luau`, draws this with a surface function, `minnaert.glsl`, on each planet's
texture. It needs PER-PIXEL LIGHTING; without it, the planets are drawn as before.

- The function applies the part of Minnaert's law that depends on the view, mu^(k-1), in linear
  light, with an exponent k for each channel, measured for each planet.
- Neptune's come from the Voyager frames: 0.680 for red, from the orange frames, as Voyager had no
  red filter, 0.712 for green and 0.768 for blue. As k is lowest in red, the limb brightens most in
  red, which makes it paler.
- Jupiter's come from OPAL's maps, whose exponents are 0.850 at 395 nm, 0.950 at 502 and 0.999 at
  631: 0.988 for red, 0.965 for green and 0.905 for blue. Jupiter's limb darkens almost as a plain
  ball's, so its function changes little, and most in blue, a faint bluish haze.
- The laws were fitted where mu is at least 0.25. Nearer the limb, the factor stays as it is there:
  for Neptune at most about 1.5 times brighter in red and 1.4 in blue, for Jupiter 1.14 in blue.
  The middle of the disk is unchanged.
- A surface function can't read where the light comes from, so the engine's own lighting stands in
  for the part that depends on the sun, mu0^k. For a planet it's the sun's cosine, softened past
  the terminator, which matches mu0^0.75 to within 1% where the sun is more than 30 degrees up, is
  13% too bright at 14 degrees, and carries light about 14 degrees past the terminator
  ([OpenReliant/openreliant#1084](https://github.com/OpenReliant/openreliant/issues/1084)).
- There's no glow outside the disk: a surface function only draws on the planet itself.

## Making it again

The scripts and the steps to run them are in the collection's
[`sources/realistic-planets`](https://github.com/OpenReliant/openreliant-mods/tree/main/sources/realistic-planets)
folder. A build downloads what each texture is made from, about 70 MB for Neptune and 93 MB for
Jupiter, and makes the same textures again.

## Credits and licences

- Voyager 2 imaging: NASA/JPL-Caltech, in the public domain, from the PDS Ring-Moon Systems Node's
  VGISS_8xxx volumes.
- Cassini imaging: NASA/JPL/Space Science Institute, in the public domain, from NASA's Photojournal
  (PIA07782).
- Hubble OPAL: this work used data acquired from the NASA/ESA HST Space Telescope, associated with
  OPAL program (PI: Simon, GO13937), CC BY 4.0, [doi:10.17909/T9G593](https://doi.org/10.17909/T9G593);
  A. A. Simon, M. H. Wong and G. S. Orton, "First results from the Hubble OPAL program: Jupiter in
  2015", The Astrophysical Journal 812 (2015).
- The spectra of Neptune and Jupiter: E. Karkoschka, "Spectrophotometry of the Jovian planets and
  Titan at 300- to 1000-nm wavelength: the methane spectrum", Icarus 111 (1994), from the PDS
  Atmospheres Node.
- Neptune's wind profile: L. A. Sromovsky, S. S. Limaye and P. M. Fry, "Dynamics of Neptune's major
  cloud features", Icarus 105 (1993).
- The textures made from the data, the thumbnail and the note are OpenReliant's, shared under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): credit OpenReliant, and for Neptune
  NASA/JPL for the Voyager data, for Jupiter NASA/JPL/Space Science Institute for the Cassini data
  and NASA/ESA Hubble OPAL for its calibration.
- The spheres, the manifest and the scripts are OpenReliant's, under the Mozilla Public License
  2.0.
