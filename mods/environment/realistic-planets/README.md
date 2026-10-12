# Realistic Planets

Replaces StarLancer's planets and moons with round, finely divided spheres, mapped from real
spacecraft and telescope imagery. This file records how the mod is made and where every picture
comes from, so that anyone can check it or make it again. The scripts are in the collection's
[`sources/realistic-planets`](https://github.com/OpenReliant/openreliant-mods/tree/main/sources/realistic-planets)
folder.

**Status:** every body the game has is done: Neptune and Triton, Uranus, Saturn and Titan, Jupiter
and its moons Io, Europa, Ganymede and Callisto, Earth and Venus. The mod needs OpenReliant 0.12.
Each body is lit by Minnaert's law in full, Saturn and its ring shade each other, Earth is a planet
with its city lights on its night side, every planet and Titan has its haze or air
([The haze](#the-haze)), and every body turns and leans as it really does, sixty times as fast.

## The game's planets

Each body but Earth comes as a detailed model and a far one, as separate object types (`0x5F` to
`0x69` and `0xC9` to `0xD3`), with 256x256 textures. Earth has one model, of type `0x6A`:

| Body | Detailed | Far | Texture |
|---|---|---|---|
| Neptune | `neptune_hi_1.shp` | `neptune_lo_1.shp` | `neptune_2` |
| Triton | `triton_hi_1.shp` | `triton_lo_1.shp` | `triton_4`, with polar caps `triton_top`, `triton_bot` |
| Uranus | `uranus_hi_1.shp` | `uranus_lo_1.shp` | `uranus_1` |
| Saturn and its ring | `saturn_hi_ring_2.shp` | `saturn_lo_ring_1.shp` | `saturn_2`, `saturn6`, and `rings_2` for the ring |
| Titan | `titan_hi_1.shp` | `titan_lo_1.shp` | `Titon_1` |
| Jupiter | `jupiter_hi_1.shp` | `jupiter_lo_1.shp` | `jupiter_1` |
| Europa | `europa_hi_1.shp` | `europa_lo_1.shp` | `europa_5` |
| Ganymede | `grany_hi_1.shp` | `grany_lo_1.shp` | |
| Io | `io_hi_1.shp` | `io_lo_1.shp` | `io_1`, `io_bot` |
| Callisto | `calist_hi_1.shp` | `calist_lo_1.shp` | |
| Venus | `venus1_hi_1.shp` | `venus1_lo_1.shp` | `venus_1`, `venus_top`, `venus_bot` |
| Earth | `earth.shp` | | `earth`, which the game's texture cache doesn't hold |

What OpenReliant's source and `sltool` show about them:

- A detailed model has two levels of detail. Neptune's near level, a 720-triangle sphere with a
  radius of 1,280,625 units, draws within 25,000,000 units; its far level, 320 triangles with a
  radius of 1,024,500, draws beyond that, out to 2,500,000,000. The far model is a 320-triangle
  sphere of the far level's size.
- The engine moves each level to stand on the middle of its vertices, works out its normals again
  from its faces, and takes the planet's radius from its last level.
- The original lights a planet with the scene's second key light alone, whose colour, (1, 1, 0.8),
  would turn the planets yellow. OpenReliant gives the planets a light of their own, which reaches
  nothing else and has the same colour unless a mod gives it another. This mod makes it white
  (`records.planet_light` in `records.luau`), so its textures hold each body's true colour.
- Neptune, Uranus, Jupiter and Venus have an atmosphere: a band that faces the camera and is added
  over the planet, sized by the planet's radius. Neptune's and Uranus's band runs from 0.85 to 0.95
  of the radius, inside the disk, so it hardly shows; Jupiter's and Venus's reach just past the
  edge, to 1.005.
- The same four planets turn about their own Y by 0.0007 of a radian each tick. With 100 ticks a
  second, that's one turn every 90 seconds. Y points down in the game's frame, and a positive turn
  about it carries this mod's maps westward. Neptune and Jupiter really turn eastward, Uranus and
  Venus's clouds westward. The mod sets each body's turn and lean
  ([Turning and leaning](#turning-and-leaning)).
- The game doesn't make Earth a planet: its sphere, with a radius of 1,048,542 units, isn't moved to
  stand on its middle, and stands 1.25 million units from the model's origin. None of the game's
  missions place Earth. The mod makes it a planet ([Turning and leaning](#turning-and-leaning)).
- Each model carries an animation clip that never plays, so the spheres here leave it out.
- The two levels of Neptune's detailed model map the texture differently from each other, so
  nothing of the original layout is worth keeping.
- Saturn's models have a second part, its ring: a flat square of 8 triangles, 9.7 million units
  across, drawn unlit, added to what's behind it, and from both sides. Its texture, `rings_2`, is a
  quarter of a disk, which draws the ring from 3.22 to 4.64 million units out, 1.25 to 1.81 of the
  planet's radius of 2,571,536 units, with a thin outer ring at 4.75 million. The real A ring reaches
  2.27 of Saturn's radius. Saturn doesn't turn, and has no atmosphere band.
- The views that come closest, from the missions' nav points and starts:

  | Body | Mission | Point | Distance from the centre, units |
  |---|---|---|---|
  | Titan | 251 | patrol_routesnapping2 | 0.82 million |
  | Ganymede | 83 | spawn_player5 | 1.05 million |
  | Titan | 25 | patrol_routewl | 1.22 million |
  | Neptune | 3 | Sci pat point 2 | 1.87 million, 0.59 million above the clouds |
  | Venus | 3 | patrol_route | 2.68 million |
  | Neptune | 4 | FinishedStorks | 3.13 million |
  | Saturn | 21 | 2nd def move in point | 3.97 million, 27 degrees above the ring's plane |
  | Saturn | 24 | Prowler1 EP | 4.83 million, in the ring's plane |

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
- Jupiter, Uranus and Saturn are flattened, as the real planets are: their spheres' polar radius is
  0.935 of their equator's for Jupiter, 66,854 km to 71,492, 0.977 for Uranus, 24,973 km to 25,559,
  and 0.902 for Saturn, 54,364 km to 60,268 (IAU). The spheres' rows of vertices stand at
  planetocentric latitudes; on a sphere both kinds of latitude agree.
- Saturn's models add its ring: a flat annulus in the plane of the equator, from 74,000 to 141,000 km
  out, the ring texture's width. It has a layer facing north and one facing south, so that the
  normals the engine works out stay flat, with 512 segments round in the detailed model and 128 in
  the far one.
- Saturn and its ring keep their real proportions, scaled so that the A ring's outer edge, 136,770 km
  out, falls where the original's ring ends, 4,640,000 units out: 33.93 units a km. The F ring then
  falls on the original's thin outer ring, and the planet's equatorial radius is 2,044,626 units, 80%
  of the original's. Around the original's planet, the real ring would reach 6 million units, and
  in mission 24 the player, who starts in the ring's plane 4.97 million units out, would start over
  the B ring. The far model's planet is 0.988 of the detailed one's size, as the original's is.
- Earth's sphere keeps the game's radius and is built where the game's stands, 1.25 million units
  from its origin. As a planet, it's moved back onto the object's place by the engine, as every
  planet is. It's a single model, as the game's is.
- Jupiter's moons and Triton keep the sizes of the game's models, which aren't in proportion to each
  other. Triton's detailed and far models both have a radius of 288,141 units.
  Europa's and Ganymede's detailed models have a radius of 288,141 units. Io's near level is uneven,
  270,744 to 273,753 units from its middle, so its sphere takes their median, 270,949. Callisto's
  are 1,280,625 units, as large as Neptune's. Europa's far model is a little larger than its
  detailed one, 331,938 units, and Ganymede's is 50 times smaller, 5,763 units, both as the game's
  are.
- The textures are named `realistic_planets_<body>`, so the game's own stay for any other model that
  uses them.

## Turning and leaning

OpenReliant keeps the planets in a table that a mod's load script can change and add to. The mod's
load script, `records.luau`, sets how each body turns and leans, and makes Earth a planet.

- Each body turns with its sidereal day from NASA's planetary fact sheets, sixty times as fast: an
  hour passes in a minute, so Jupiter, the fastest, turns once every ten minutes, and Earth once
  every 24. `TIME_SCALE` at the top of the script sets the factor.
- North is the pole the International Astronomical Union names, on the north side of the solar
  system, at the top of each texture. Neptune, Saturn, Jupiter and Earth turn eastward, Uranus and
  Venus westward.
- Venus's map shows its cloud tops, which turn westward once in about five days, as Akatsuki's maps
  show ([Venus](#venus)), so Venus turns with them rather than with its ground, which takes 243
  days.
- Each pole leans from the pole of the planet's orbit by its obliquity: Neptune's by 28.32 degrees,
  Uranus's by 82.23, Saturn's by 26.73, Jupiter's by 3.13, Venus's by 2.64 and Earth's by 23.44. The
  game has no orbits, so the mission's frame stands in: a pole leans from the planet's up as the
  mission places it.
- A moon turns once an orbit, as Io, Europa, Ganymede, Callisto, Titan and Triton do, and leans as
  its planet does, since it orbits in the plane of its planet's equator. Triton turns westward, as
  it orbits Neptune, about a pole some 30 degrees from the solar system's north.
- Every pole leans toward its body's left, -X, as the mission places it, as the game has no seasons
  to take the way from. Leaned this way, Saturn's ring shows open from where the player starts each
  of the game's missions with Saturn, by 8 to 37 degrees. Unleaned, it's within 3 degrees of edge on
  in four of them.
- Earth becomes a planet, so the sun alone lights it, as it lights the others, and its night side is
  dark but for its city lights ([City lights](#city-lights)).
- The band the game draws over the rim of Neptune, Uranus, Jupiter and Venus is left out: each
  planet's limb law, fitted to its measured photometry, already gives the rim its light
  ([The limb](#the-limb)).

## Neptune

The map is made from 34 calibrated Voyager 2 frames taken on 17 and 20 August 1989, with the colour
taken from a ground-based spectrum of Neptune. The note
[`neptune-voyager-map.pdf`](neptune-voyager-map.pdf) in this folder describes the method in detail,
with figures and references.

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| Voyager 2 imaging, through the [PDS Ring-Moon Systems Node](https://pds-rings.seti.org/) | Calibrated narrow-angle frames from the 1989 flyby | Public domain (NASA/JPL) | Yes |
| The same at high phase, through [OPUS](https://opus.pds-rings.seti.org/) | Calibrated wide- and narrow-angle frames of the lit limb at 136 to 153 degrees of phase, and of the whole crescent at 133 | Public domain (NASA/JPL) | Yes, 9 frames for the haze |
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

In true colour, Neptune's brightness varies by only a few per cent, which looks featureless on a
game screen, so the texture stretches the brightness's differences from the mean threefold, as
Voyager's published pictures of Neptune were stretched. The mean colour stays the same.

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
| Cassini's frames at high phase, through [OPUS](https://opus.pds-rings.seti.org/) | Narrow-angle frames at 120 degrees of phase and more, from 18 million km, about 110 km a pixel | Public domain (NASA/JPL/Space Science Institute) | No: far coarser than the haze |
| Galileo's frames of the limb at 144 and 156 degrees, through OPUS | Violet and 756 nm frames of December 1996, 13 to 16 km a pixel | Public domain (NASA/JPL) | No: raw, and compressed with loss |
| X. Zhang, R. A. West and others (2013); D. Banfield and others (1998) | The stratospheric haze's particles and height from Cassini's frames at several phases, and its optical depth from Galileo's | Published values | For the haze |
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

The game turns Jupiter westward. The mod turns it eastward, as it really turns
([Turning and leaning](#turning-and-leaning)).

## Uranus

Uranus's map is Hubble's OPAL map of November 2022, with its colour taken from Karkoschka's spectrum.

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| [Hubble OPAL](https://archive.stsci.edu/hlsp/opal), November 2022 | Calibrated maps at 467, 547 and 657 nm, in I/F, the limb darkening taken out by Minnaert's law, at 0.5 degrees a pixel in planetographic latitude | CC BY 4.0 | Yes |
| Hubble OPAL, the other years from 2014 to 2025 | The same, once a year | CC BY 4.0 | No: 2022 shows the bright north polar cap that formed in the 2010s, and still reaches the southern low latitudes |
| Voyager 2, 1986 | Images of the south, which faced the sun then | Public domain | No: in visible light Uranus looked almost featureless to it |
| E. Karkoschka's spectra, through the [PDS Atmospheres Node](https://pds-atmospheres.nmsu.edu/) | Uranus's geometric albedo from 300 to 1000 nm, measured in July 1993 | NASA Planetary Data System | For the colour |

### The map

- Uranus is small seen from Earth, so Hubble's map holds about half a degree a pixel. The texture is
  soft, but Uranus has few sharp features.
- OPAL's files hold the north first and put 0 degrees east at the right edge, east increasing to the
  left, as their readme says, so the texture reverses their columns to put east to the right, as
  seen from outside. The drift of the clouds between the two rotations Hubble mapped couldn't
  confirm this, as Uranus shows too few; its bands and polar cap look the same either way round.
- Hubble sees the north, which faces the sun. Past about 9 degrees south the maps grow noisy, seen
  near the limb, so the data is trusted only where the brightness varies by less than 1% from one
  pixel to the next along a latitude. Past that, the northern hemisphere's bands at the same
  latitude fill the south, averaged along each latitude over 45 degrees and blended in over 10. It's
  a plausible guess, not data: Voyager 2 saw a bright south polar cap in 1986, as Hubble sees a
  northern one now.
- OPAL's latitudes are planetographic. The texture's are planetocentric, as the flattened spheres
  take them.

### Colour, contrast and brightness

- The colour is Karkoschka's spectrum of Uranus through the CIE 1931 observer, as for Neptune: sRGB
  (159, 196, 202), a pale cyan. At each place it's varied by the three maps' ratios to their means,
  as Neptune's is by Voyager's filters.
- Nearly all of Uranus's contrast is in the red map: from the 10th to the 90th percentile it varies
  by 1.58 at 657 nm, against 1.03 at 467 nm and 1.09 at 547. For the game, the luminance's contrast
  is stretched threefold on its logarithm, as Neptune's and Jupiter's are, keeping each place's
  colour; stretching each map instead turns the polar cap pink.
- At its true normal albedo, 1.19 times the spectrum's geometric albedo at 547 nm, Uranus's mean
  luminance is about 0.61, a fifth more than Neptune's (0.50). The game's tone curve compresses the
  top of the range, so past Neptune's level a brighter texture mostly pales Uranus towards white. The
  texture's mean luminance is 0.55: a little brighter than Neptune, as the real planet is, with fewer
  near-white pixels on its lit disk than Neptune shows, but less colour, as the real planet is paler.

Uranus really turns westward, about a pole that leans 82 degrees, and the mod turns it so
([Turning and leaning](#turning-and-leaning)).

## Saturn

Saturn's map takes its detail from Cassini's global maps of August 2011, the brightness of its bands
from Hubble's calibrated maps of August 2025, and its north polar cap from Hubble's maps of June 2018.
Its colour comes from Karkoschka's spectrum. Its ring is made from Voyager 2's measurements and
Cassini's colours.

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| [Cassini's global maps](https://atmos.nmsu.edu/data_and_services/atmospheres_data/Cassini/sat_global_map.html), by L. Li, R. A. West, X. Jiang and B. Knowles | Maps in Cassini's red, green and blue filters from 11 August 2011, at 0.1 degrees a pixel, made from frames of about 160 km a pixel | NASA Planetary Data System | Yes, for the detail |
| [Hubble OPAL](https://archive.stsci.edu/hlsp/opal), August 2025 | Calibrated maps from 395 to 763 nm, in I/F, the limb darkening taken out by Minnaert's law, at 0.2 degrees a pixel. Three months after Saturn's equinox, both hemispheres show | CC BY 4.0 | Yes, for the bands' brightness, and where Cassini's maps hold nothing |
| Hubble OPAL, June 2018 | The same, of the north, seen from 26 degrees above | CC BY 4.0 | For the north polar cap and its hexagon |
| E. Karkoschka's spectra, through the [PDS Atmospheres Node](https://pds-atmospheres.nmsu.edu/) | Saturn's albedo from 300 to 1000 nm, measured in July 1993 | NASA Planetary Data System | For the colour |
| Voyager 2's photopolarimeter, through the [PDS Ring-Moon Systems Node](https://pds-rings.seti.org/voyager/pps/profiles.html) | The rings' optical depth, measured as they passed in front of the star delta Scorpii in August 1981, at 10 km a sample | Public domain (NASA/JPL) | For how much light the ring stops |
| Voyager 2's imaging, through the same node | The lit rings' brightness in I/F, from its finest mosaic of them, August 1981, at 10 km a sample | Public domain (NASA/JPL) | For the ring's brightness |
| [Cassini's sweep across the rings](https://pds-rings.seti.org/press_releases/pages/PIA11xxx/PIA11142.html) (PIA11142) | A natural colour mosaic across the lit rings, November 2008 | Public domain (NASA/JPL/Space Science Institute) | For the ring's colour |
| Cassini's wide-angle camera at high phase, through [OPUS](https://opus.pds-rings.seti.org/) | Frames calibrated to I/F with CISSCAL, from the COISS_2052 and COISS_2080 volumes, with their geometry from OPUS and the clock angle of Saturn's pole from the volumes' indexes | Public domain (NASA/JPL/Space Science Institute) | Yes, 9 frames in the blue, green and red filters from 2009 and 2013, for the haze |

### The planet's map

- Cassini's maps resolve about twice as much as Hubble's, but they need work before they can be used:
  - Their values are levels for display, not I/F. Their makers took the light's angle out by a
    method of their own, and stretched each filter's map on its own: measured against Hubble's maps
    over the same latitudes, they have 2.1 to 5.3 times the contrast, the green the most. So each
    filter's contrast is brought to Hubble's at its wavelength, and along each latitude the maps are
    scaled to Hubble's mean there, smoothed over 3 degrees. The bands' brightness is then Hubble's,
    calibrated, and the detail Cassini's.
  - The pieces of the mosaic meet in seams at ten longitudes. Each row's step at a seam is taken out
    and spread over 5 degrees either side. The pieces were taken hours apart and the winds moved the
    clouds between them, so where the clouds don't line up across a seam, the map is blurred a
    little along the latitude there.
  - In August 2011 the sun stood 10.7 degrees north of the rings, so their shadow blanks the maps
    from 5.4 to 17.1 degrees south, and the C ring's thin shadow darkens the latitudes between that
    and the equator. A few bands have streaks, where the maps were drawn from too few of the frames'
    pixels: near the equator, and at 12 and 70 degrees north. They're found as rows whose fine detail
    repeats on the row half a degree south, which clouds' detail doesn't.
  - Hubble's maps fill all of those, the equator, and the poles past 79 degrees north and 82 south,
    blended over 1.5 degrees.
- Hubble's maps of 2025 show both hemispheres, from 84 degrees south to 77 north:
  - Moons and their shadows cross them, and are filled from their latitude around them.
  - Hubble mapped Saturn twice, 9.4 hours apart. In between, the clouds near the equator moved 14
    degrees east, about 450 m/s, as Saturn's equatorial jet blows, which confirms that the files put
    east to the right. The second map is moved back by the winds measured at each latitude, and the
    two are averaged.
  - Near the equator, broad patches along each latitude, where Hubble's orbits meet, are taken out,
    and the line along the equator where the rings and their shadow crossed the disk is filled from
    the latitudes either side.
  - The 467 nm maps aren't used: their limb-darkening exponent, 0.86 against 0.65 at 502 nm,
    over-corrects near the limb, so that at 70 degrees north they read brighter than the 502 nm
    maps, which Saturn's spectrum never does.
- Past 77 degrees north Hubble saw the clouds edge on in 2025, so the north polar cap, with Saturn's
  hexagon, comes from the maps of June 2018, when Hubble saw the north from 26 degrees above. It's
  scaled to 2025's brightness and blended in from 70 to 76 degrees. Past 84 degrees south the map
  fades into the last degrees' mean colour.
- The map keeps System III longitudes, 0 in the middle column. The game doesn't turn Saturn, and the
  mod turns it eastward with System III's period ([Turning and leaning](#turning-and-leaning)).

### Colour, contrast and brightness

- The colour is Karkoschka's spectrum of Saturn through the CIE 1931 observer, as for Neptune: sRGB
  (195, 184, 153), a pale cream yellow. At each place it's varied by Cassini's three maps' ratios to
  their means.
- For the game, the luminance's contrast is stretched threefold, as the other planets' is.
- At its true normal albedo, 1.16 times the spectrum's geometric albedo at 502 nm, Saturn's mean
  luminance is about 0.56. The texture's is 0.22, the same share of its true brightness as
  Jupiter's 0.3 is of Jupiter's, so the two keep their real proportion.

### The ring

- The ring's texture, `realistic_planets_saturn_rings`, is a strip of 4096 by 8 texels, 16 km each,
  from 74,000 to 141,000 km out, every row alike.
- Its alpha is the share of the light the ring stops seen face on, 1 - exp(-tau), from the optical
  depth tau that Voyager 2 measured as the star shone through the rings: about 0.1 in the C ring and
  the Cassini Division, 0.5 in the A ring, and 1.6 and more in the B ring, whose core hid the star.
- Its colour's brightness is the reflectance of the ring's particles. Voyager 2's camera measured how
  bright the lit rings are, with the sun 8 degrees above them and the camera 23 degrees above. Light
  scattered once in a layer of optical depth tau gives
  I/F = S mu0 / (mu + mu0) (1 - exp(-tau (1/mu + 1/mu0))), where mu and mu0 are the cosines of the
  view's and the sun's angles from the ring's pole, and that gives S, the particles' reflectance:
  about 0.09 in the C ring, 0.27 in the B ring, 0.14 in the Cassini Division and 0.21 in the A ring.
  The C ring's particles are the darkest, as they really are.
- Its hue comes from Cassini's natural colour mosaic across the lit rings, put at its radii by eight
  ring edges that both it and Voyager's mosaic show sharply, and smoothed over 300 km.
- The B ring at its brightest, seen and lit from the same height, is as bright as the planet's
  equatorial zone seen and lit from overhead, as the two look about alike from Earth.
- The mod's player script draws the ring with a surface function, `rings.glsl`, registered
  see-through. Seen at a slant, the ring lets less of the light behind it through, exp(-tau / mu),
  so the C ring is see-through face on and opaque edge on. On the side the sun lights, its particles
  scatter the share of the sunlight the law above gives toward the eye. On the other side the light
  comes through the ring: S mu0 / (mu - mu0) (exp(-tau / mu) - exp(-tau / mu0)), so seen from there
  the C ring and the Cassini Division glow and the B ring is dark, as they really do.
- Where Saturn stands between the ring and the sun, the ring gets no sunlight: the function follows
  each pixel's ray toward the sun, in Saturn's own frame, to the flattened planet. So the planet's
  shadow falls across the ring, as wide as the planet.
- Saturn's own surface function, `saturn.glsl`, shades the planet by the ring. Each pixel's ray
  toward the sun crosses the ring's plane at some radius, and where the ring is, it lets through
  exp(-tau / mu0) of the sunlight, tau taken from the ring's texture in 128 steps from its inner
  edge to its outer. The B ring's shadow is the darkest, and the Cassini Division's and the C ring's
  are light.
- The game blends colours as they're encoded, not in linear light, so a faint layer that looks right
  against the black sky comes out too bright over the planet. The function sets its colour and alpha
  so that the result is exact over the sky, and right over a planet behind it at about 0.5 encoded.

### Sharper maps

These are the sharpest open global maps of Saturn there are. At mission 21's viewpoint, the closest,
the middle of the disk shows about 116 km a pixel at 1080p, against the map's 160 or so. A sharper
map would take a mosaic of Cassini's own frames, taken on many days
([#34](https://github.com/OpenReliant/openreliant-mods/issues/34)).

## Venus

Venus's map shows the markings of its cloud tops in ultraviolet, from Akatsuki's maps of June 2022,
made faintly visible on Venus's own colour. To the eye Venus is nearly blank: the markings come from
an absorber in the clouds that dims them by up to a quarter at 365 nm, but only by a few per cent in
the blue, and hardly at all in green and red.

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| [Akatsuki's UVI maps](https://doi.org/10.17597/isas.darts/vco-00016), by S. Murakami and others | Maps of the radiance at 283 and 365 nm, at 0.125 degrees a pixel, every two hours from 2015 to 2024, with each cell's angles of the light and the view | CC BY 4.0 | Yes, 13 maps at 365 nm from 25 to 29 June 2022 |
| [Akatsuki's IR1 maps](https://doi.org/10.17597/isas.darts/vco-00017) | The same at 0.90 µm, in 2016 | CC BY 4.0 | No: Venus Express measured the visible itself |
| Venus Express's camera, VMC, through [ESA's Planetary Science Archive](https://archives.esac.esa.int/psa/ftp/VENUS-EXPRESS/VMC/) | Pictures at 365, 513, 965 and 1010 nm from 2006 to 2014, with each pixel's latitude and angles | CC BY-NC 3.0 IGO | For the limb |
| A. Mallama, B. Krobusek and H. Pavlov (2017) | Venus's geometric albedos in the Johnson and Sloan bands, and its phase curves | Published values | For the colour |
| A. Payne and others (2025) | Venus's spectrum, from MESSENGER's spectra of one region, scaled to Mallama's albedo in V | Published values | No: yellower than Venus seen whole, B-V 0.92 |
| M. Luginin and others (2016) | The upper haze from Venus Express's SPICAV IR, 222 solar occultations from 2006 to 2014: its droplets' sizes and numbers, and its scale height | Published values | For the haze |
| J. E. Hansen and J. W. Hovenier (1974) | The cloud droplets' refractive index and spread of sizes, from the polarisation of Venus's light | Published values | For the haze's droplets |

### The map

- The texture is made from 13 of Akatsuki's maps, about 8 hours apart, over about one turn of the
  cloud tops. Akatsuki saw Venus then at phase angles of 17 to 44 degrees. Two weeks before, it saw
  Venus from near the sun's direction, and those maps show the glory: bright rings that the cloud
  droplets throw back toward the sun, which move with the camera.
- Each map's limb darkening is taken out with Minnaert's law, I/F = B mu0^k mu^(k-1). The exponent k
  is fitted to each map with each latitude's own brightness, so that the bands' brightness, darker
  near the equator where the sun stands highest, doesn't count as limb darkening. The maps' mean,
  0.86, is taken out of all of them alike. Fitted as one law over the whole map, k comes out near
  0.72, as the dark equator reads as part of the law.
- The clouds turn about 3 degrees an hour westward near the equator, about 90 m/s, measured by
  matching the clouds' detail between every two maps less than a day apart. More than 35 degrees
  from the equator the views are too slanted for the clouds to be followed, and the rate is held at
  its last value. Venus's clouds really turn westward, once in about five days, and the mod turns
  Venus with them ([Turning and leaning](#turning-and-leaning)).
- The maps are moved back by the winds to the middle of the four days and averaged. The clouds
  change over those days, so where two views meet, they differ. The maps' broad brightness is
  blended over wide margins, so that no seam shows, and their detail comes from the view that sees
  each place best, so that it stays sharp.
- A few maps hold ghosts of the camera: bright patches a few degrees across that the maps before and
  after don't show. Where one view is much brighter than all the others, it's left out.
- Where the clouds weren't seen, the mean of what was seen nearby fills in, and farther away the
  latitude's mean. Past 60 degrees, where the views are slanted and few, the map fades into each
  latitude's mean, and the poles hold the mean of the last latitudes seen most of the way round.

### Colour, markings and brightness

- Venus's colour comes from its geometric albedos in the Sloan bands and the Johnson B and V bands,
  joined into a spectrum and taken through the CIE 1931 observer, as for the others. Those albedos
  are for full phase, where Venus can't be seen from Earth, and the paper's own phase curves make it
  yellower at the phase angles where it is seen: its B-V is 0.70 at full phase and 0.81 at 45
  degrees, close to the 0.82 usually quoted. The texture takes the colour at 45 degrees: sRGB (219,
  215, 201), a pale cream.
- The ultraviolet absorber's effect fades toward red. Its share at each wavelength, of its effect at
  365 nm, is taken as the spectrum's shortfall below its highest albedo, on the logarithm, over the
  shortfall at 365 nm: about half at 400 nm, a quarter at 436 and a twentieth at 549. Each place's
  spectrum is darkened by its ratio to the mean at 365 nm, raised to that share, so the dark
  markings are a little yellower as well as darker.
- For the game, the markings are four times as strong as the eye would see them: the blue varies by
  about a quarter either way, the green by a few per cent.
- Venus's geometric albedo has 1.36 times the luminance of Jupiter's, and both darken toward the
  limb about as a plain ball does (see below), so the texture's mean luminance is 0.41, 1.36 times
  Jupiter's 0.3.

## Titan

Titan's map shows its haze as Cassini saw it in visible light, with the surface underneath showing
faintly through. To the eye Titan is an almost featureless orange ball: the haze hides the surface,
which only shows in the near infrared. Beyond the disk the haze shows as Cassini saw it too: a thin
blue fringe from the front, and with the sun behind Titan, a bright ring round the dark disk.

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| Cassini's narrow-angle camera, through the [PDS Ring-Moon Systems Node](https://pds-rings.seti.org/) | Frames calibrated to I/F with CISSCAL, from the COISS_2060 volume, with their geometry from the volume's index | Public domain (NASA/JPL/Space Science Institute) | Yes, 12 frames in the blue, green and red filters from January and February 2010, for the texture and the haze |
| The same camera at high phase, through [OPUS](https://opus.pds-rings.seti.org/) | Frames calibrated to I/F with CISSCAL, from the COISS_2053 to COISS_2064 volumes, with their geometry from OPUS and the clock angle of Titan's pole from the volumes' indexes | Public domain (NASA/JPL/Space Science Institute) | Yes, 33 frames in the blue, green and red filters from February 2009 to August 2010, for the haze |
| [PIA22770](https://science.nasa.gov/photojournal/titan-mosaic-the-surface-under-the-haze), "Titan Mosaic: The Surface Under the Haze" (2018) | Cassini's map of the surface's normal albedo at 938 nm, from 9,873 frames taken over 13 years, the haze taken out with a model of it, at 16 pixels a degree | Free to use with credit (JPL's image use policy) | Yes, for the surface |
| [The USGS's global mosaic of Titan](https://astrogeology.usgs.gov/search/map/titan_cassini_iss_global_mosaic_4005m) | The surface at 938 nm from Cassini's frames, at about 4 km a pixel | Public domain | No: PIA22770 is sharper |
| E. Karkoschka's spectra, through the [PDS Atmospheres Node](https://pds-atmospheres.nmsu.edu/) | Titan's geometric albedo from 300 to 1000 nm, measured in July 1993 | NASA Planetary Data System | For the colour |

### The haze

- Cassini's narrow-angle camera took four sets of frames of Titan in its blue, green and red filters,
  on 30 January and 16 February 2010, months after Titan's equinox, with the sun over its equator
  and both poles lit. Titan is about 800 pixels across in them, at phase angles of 28 to 50 degrees.
- Each frame's disk is fitted to its lit limb, where the brightness falls to half of that just inside
  it. That's the haze's edge in the filter, at 28 to 33 degrees of phase about 2,710 km from the
  centre in red, 2,730 km in green and 2,840 km in blue, and about 30 km higher at 50 degrees. The
  game's sphere stands for green's, 2,741 km over the four sets.
- Each pixel's latitude and the cosines of its angles of light and view come from the disk, the
  frame's sub-spacecraft and sub-solar points, and the angle of Titan's north pole in the frame, from
  the volume's index. The sun's cosine follows the frames' brightness closely, which confirms the
  orientation.
- Minnaert's law is fitted to each frame where both the sun and the view are more than 15 degrees
  above the horizon, with each band of 5 degrees of latitude given its own brightness, as for Venus.
  A band's brightness over the frame's mean within 60 degrees of the equator is the haze's profile in
  that filter, and the four sets' profiles are averaged. The frames see from 72.5 degrees south to
  72.5 north, and past that the profile keeps its last value.
- In 2010 the haze is brighter in the south than in the north, most in blue: in blue, 1.24 times the
  mean in the far south and 0.75 at 62 degrees north, and in red, 1.13 and 1.03.

### Colour, surface and brightness

- The colour is Karkoschka's spectrum of Titan through the CIE 1931 observer, as for the others,
  bent at each latitude through the three filters' profiles, as Saturn's is through its maps. At the
  equator it's sRGB (141, 124, 94), a dull orange.
- At 938 nm the haze is thin enough for Cassini to see the surface, and PIA22770 maps its normal
  albedo there: the dark dune fields round the equator, the bright Xanadu, and the lakes and seas
  near the poles. The map's columns run east from 0 degrees at its left edge. The texture shows the
  map's contrast at 0.15 of its strength, on the logarithm, over the haze's colour, so that the
  surface shows faintly through the haze.
- At its true normal albedo, 1.39 times the spectrum's geometric albedo by Minnaert's law in green,
  Titan's mean luminance is about 0.31. The texture's is 0.12, the same share of its true brightness
  as Jupiter's 0.3 is of Jupiter's.

## Jupiter's moons

Io's, Europa's, Ganymede's and Callisto's maps take their detail from the USGS's global maps, made
from Voyager's and Galileo's pictures, and their colour from Voyager's colour frames of 1979. Most
published pictures of these moons are false colour: they show near-infrared light as red and turn
the colour up, to show what the ground is made of. Here they're in true colour: Io a pale yellow
with whiter frost plains and black volcanoes, Europa a creamy white with tan streaks and a darker,
browner trailing side, and Ganymede and Callisto a faintly warm grey.

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| [The USGS's global maps](https://astrogeology.usgs.gov/search/map/jupiter-voyager-and-galileo-global-mosaics) | Greyscale maps of each moon from Voyager's and Galileo's pictures, the light's angles taken out, at 1 km a pixel, Europa's at 500 m | Public domain | Yes, for the detail |
| The USGS's colour maps of Ganymede and Io | Galileo's violet, green and near-infrared pictures shown as blue, green and red, Ganymede's "enhanced using commercial software" | Public domain | No: false colour |
| Voyager 1's and 2's narrow-angle camera, through the [PDS Ring-Moon Systems Node](https://pds-rings.seti.org/) | Frames of 1979 in violet, blue, green and orange, calibrated to I/F with the camera's distortion removed | Public domain (NASA/JPL) | Yes, 55 colour sets, for the colour and the limb |
| Galileo's camera, through the same node | Frames of 1996 to 2003 | Public domain (NASA/JPL) | No: only the raw frames are there |
| Cassini's camera, in its flyby of Jupiter in 2000 and 2001 | Calibrated frames, the moons at 55 km a pixel at best | Public domain (NASA/JPL/Space Science Institute) | No: Voyager's frames are much sharper |
| [Constantine Thomas's mosaic of Ganymede](https://www.planetary.org/space-images/20130620_ganymedevgr2) (2013) | Voyager 2's close-up frames of one side, at 2 km a pixel, orange, blue and violet shown as red, green and blue | CC BY 3.0 | No: one side only, and not true colour |
| [NASA's Jovian Satellite Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/joviansatfact.html) | The moons' visual geometric albedos | Public domain | For the brightness |

### The maps

- The USGS's maps hold 11,445 by 5,723 pixels for Io, 19,631 by 9,816 for Europa, 16,539 by 8,270
  for Ganymede and 15,138 by 7,569 for Callisto. Each joins many pictures, with the light's angles
  taken out by a Lunar-Lambert function, so they hold the ground's brightness.
- Their columns run east from their left edge, which stands at 0 degrees for Europa, Ganymede and
  Callisto and at 180 west for Io, as their GeoTIFF tags give. Landmarks confirm it: Valhalla on
  Callisto, Tros and Osiris on Ganymede, and Loki, Pele and Prometheus on Io.
- Their values rise from 0.5 in proportion to the ground's brightness. Io's, Europa's and Ganymede's
  GeoTIFF tags say so, and with the tags' scale, the maps' means come to 0.64 for Io and 0.43 for
  Ganymede, against geometric albedos of 0.62 and 0.44, and 0.88 for Europa, the brightest.
  Callisto's map carries no such tags, and is taken to rise from the same value.
- Where the maps hold nothing, around Callisto's south pole and at the other maps' polar edges, the
  texture takes each latitude's mean. The maps join pictures of very different sharpness, so in
  places sharp strips meet blurred ground, with small steps of brightness between them.

### The Voyager frames

- `frames.json` lists one colour set for each 20 degrees of each moon's longitude, the set with the
  largest disk: violet, blue, green and orange frames taken within minutes, by Voyager 1 in February
  and March 1979 or Voyager 2 in June and July, the moon 55 to 945 pixels across. That's 11 sets of
  Io, 14 of Europa, 14 of Ganymede and 16 of Callisto. Two green frames of Io and an orange frame of
  Ganymede are left out, as they show nothing or only noise. Io's sets see it all round, but from
  about 280 to 330 degrees west only at a slant.
- The camera's pointing isn't archived for 1979 either, so `fit.py` fits it to each frame and keeps
  it in `fits.json`. The disk's size comes from the moon's distance, so each sharp edge in the frame
  votes for the point a radius inward along its gradient, and the lit limb's votes meet at the
  centre. The twist, where north points, comes from matching the frame against the moon's map, seen
  as the frame would see it, at twists all round. Then the limb is fitted to a fraction of a pixel.
  A set's frames share their twist, and a frame that strays from its set's is fitted again near it.
- The frames match the maps closely: by a correlation of 0.88 on Europa and 0.87 on Ganymede, the
  median of their frames, 0.75 on Callisto, whose disks are the smallest, and 0.71 on Io, whose
  ground its volcanoes changed between Voyager's visits and Galileo's. The limbs fit to about a
  quarter of a pixel on Europa, Ganymede and Callisto, and to a pixel on Io, where the largest disks
  miss by up to six, as Io isn't quite round.
- Each frame's sky, more than 1.2 of the disk's radii from its centre, is taken off it first: most
  frames read within half a per cent of the disk's brightness there, but a few several per cent.

### Colour, detail and brightness

- Each set's frames are mapped onto latitude and longitude with their limb darkening taken out, and
  the violet, blue and orange maps are divided by the green one. The four frames share a phase
  angle, so the ratios hold the colour alone. The sets' ratios are averaged, the best view of each
  place counting the most.
- On these moons, darker ground is redder. So each ratio is fitted to the map's brightness, and at
  each texel the colour follows the texel's own brightness, a small bright crater taking the bluer
  colour of bright ground, times what the fit leaves, smoothed over six of the frames' pixels: from
  about 2.5 degrees on Io to 9 on Callisto, whose frames are the coarsest. Io's colour follows its
  frames the most, as its yellow sulphur, white frost and dark lava don't line up with brightness
  alone.
- Each texel's spectrum runs through the filters' wavelengths, 416, 479, 566 and 591 nm, straight
  between them and flat beyond, and is taken through the CIE 1931 observer, as for the other bodies.
  At their true brightness, the moons' mean colours are sRGB (231, 225, 175) for Io, (235, 232, 206)
  for Europa, (186, 183, 163) for Ganymede and (129, 125, 109) for Callisto.
- Each texture's mean luminance is the same share of the moon's true brightness as Jupiter's 0.3 is
  of Jupiter's: 0.29 for Io, 0.31 for Europa, 0.18 for Ganymede and 0.08 for Callisto, from NASA's
  visual geometric albedos of 0.62, 0.68, 0.44 and 0.19 and Minnaert's law in green.
- Ganymede's texture is 8192 by 4096, as mission 83 shows it from close by; the other moons' are
  4096 by 2048.

## Triton

Triton's map takes its detail from the USGS's global colour mosaic, which Paul Schenk made from
Voyager 2's pictures, and its colour from Voyager 2's colour frames of 1989, as Jupiter's moons do.
Published pictures of Triton turn its colours up, into pinks and greens. In true colour it's a pale
cream-white, brightest on its south polar cap, which dark streaks cross, and greyer nearer the
equator.

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| [The USGS's global colour mosaic of Triton](https://astrogeology.usgs.gov/search/map/triton_voyager_2_global_color_mosaic_600m) (PIA18668, 2014) | Paul Schenk's map from Voyager 2's pictures, at 600 m a pixel, its orange, violet and ultraviolet frames shown as red, green and blue | Public domain (NASA/JPL/Lunar and Planetary Institute) | Yes, its violet band for the detail |
| Voyager 2's narrow-angle camera, through the [PDS Ring-Moon Systems Node](https://pds-rings.seti.org/) | Frames of 1989 in violet, blue, green and orange, calibrated to I/F with the camera's distortion removed | Public domain (NASA/JPL) | Yes, 14 colour sets, for the colour and the limb |
| [NASA's Neptunian Satellite Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/neptuniansatfact.html) | Triton's visual geometric albedo | Public domain | For the brightness |

### The map

- The map holds 14,138 by 7,069 pixels, its columns running east from 180 degrees west, as its
  GeoTIFF tags give. Its bands come from Voyager 2's orange, violet and ultraviolet frames, as the
  USGS's record says. Its middle band, the violet one, gives the detail, as of the three it matches
  Voyager's green frames best.
- Its contrast was stretched for display. Matched against the green frames, each with the map
  blurred to the frame's sharpness, the map's values rise in proportion to the ground's brightness
  from -171 on its scale of 0 to 255, the median of the frames at least 90 pixels across. So the map
  shows about twice the real contrast. With that zero, the frames' brightness follows the map's to
  within about 4% across their disks.
- Voyager 2 flew past in Triton's southern summer, with its north in the dark. The map holds the
  south, and the north up to 45 degrees at the longitudes Voyager saw best and 3 degrees at the
  worst: two thirds of the globe. The rest of the north takes the ground at the opposite latitude, 180
  degrees round, blended in over 10 degrees from what was seen nearest. It's a plausible guess, not
  data, as Uranus's south is: the north may have a polar cap like the south's, or none.

### The Voyager frames

- `frames.json` lists every colour set Voyager 2 took of Triton with its disk at least 40 pixels
  across, from 19 to 25 August 1989: 17 sets, each a green frame with one to three of the violet,
  blue and orange frames taken within 15 minutes of it. Triton is 44 to 675 pixels across in them, at
  phase angles of 12 to 39 degrees, and they see it all round, from 13 to 55 degrees south of its
  equator.
- `fit.py` fits their pointing as for Jupiter's moons. 41 of the 50 frames fit: those at least 90
  pixels across match the map by a correlation of 0.86, the median, with their limbs to a quarter of
  a pixel. The other nine, mostly from the smallest disks, give a twist that strays from their set's
  and are left out. Three sets lose their green frame with them, so 14 sets give the colour.

### Colour, detail and brightness

- The colour comes from the sets' ratios to green, fitted to the map's brightness, as for Jupiter's
  moons, with each set's ratios for the filters it has. At the mean brightness, violet is 0.81 of
  green, blue 0.89 and orange 0.95: the spectrum rises from violet to green and dips a little in
  orange. Brighter ground is a little bluer. Each set's whole-disk colour, straight from its frames,
  agrees to within a few per cent.
- At its true brightness, Triton's mean colour is sRGB (243, 244, 229), a pale cream-white.
- The texture's mean luminance is 0.35, the same share of Triton's true brightness as Jupiter's 0.3
  is of Jupiter's, from NASA's visual geometric albedo of 0.72 and Minnaert's law in green.
- The texture is 4096 by 2048.

## Earth

Earth's map is NASA's Blue Marble of 2002, clouds and all, with the haze of the air added back as
GOES-18 sees it from space. The Blue Marble shows the ground with the air taken out, the sea almost
black. Seen from space, the air's haze lights the sea up blue and softens the land, as DSCOVR's
pictures of the whole Earth show.

None of the game's missions place Earth, so only new missions show it. The mod makes Earth a
planet, and its night side shows its city lights, from NASA's Black Marble
([City lights](#city-lights)).

### Sources considered

| Source | What it is | Licence | Used |
|---|---|---|---|
| [NASA's Blue Marble](https://science.nasa.gov/resource/blue-marble/) (2002), `land_ocean_ice_cloud_8192.tif` | Months of MODIS's pictures from Terra of the land, the sea, the sea ice and the clouds, joined into one true-colour map of 8192 by 4096 | Public domain (NASA Goddard Space Flight Center) | Yes |
| NASA's Blue Marble: Next Generation (2004) | A map of each month at 500 m a pixel, without clouds | Public domain | No: its clouds would have to come from elsewhere |
| [NASA's Black Marble](https://earthobservatory.nasa.gov/features/NightLights) (2016), `BlackMarble_2016_3km.jpg` | Earth's city lights on clear nights of 2016, from VIIRS on Suomi NPP, over a dark blue picture of the ground, 13,500 by 6,750 | Public domain (NASA Earth Observatory) | Yes, for the city lights |
| [GOES-18's and GOES-19's full-disk pictures](https://registry.opendata.aws/noaa-goes/), ABI L2 MCMIP | The whole disk every 10 minutes from 137 and 75 degrees west, as I/F in 16 bands at 2 km a pixel | Public domain (NOAA) | Yes, the pair of 21 June 2025 at 21:00 UTC, for the haze and the limb |
| DSCOVR's camera, EPIC | Earth's whole sunlit disk from the L1 point | Public domain (NASA) | No: its calibrated data needs a login |
| [NASA's Earth Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html) | Earth's visual geometric albedo | Public domain | For the brightness |

### The map

- The Blue Marble shows MODIS's red, green and blue bands, at 645, 555 and 469 nm, as sRGB's red,
  green and blue, as NASA's true-colour pictures do. Its columns run east from 180 degrees west, so
  Africa is in the middle. The texture is 4096 by 2048.
- Unlike the other bodies' spectra, its three bands aren't taken through the CIE 1931 observer: three
  points hold too little of a spectrum, and drawn straight between them, the forests' narrow green
  peak turns olive. So NASA's colours stand.

### The haze

- Over the South Pacific, 12 to 40 degrees south and 115 to 165 west, away from the sun's glint,
  GOES-18 saw the clear sea at 23% of thick clouds' brightness in blue and 7% in red, with the sun 37
  degrees high, the satellite 54 degrees high and a phase angle of 19 degrees. The Blue Marble shows
  the same sea at 3% of its clouds in blue and nothing in red.
- So each band is the Blue Marble's, times what the air lets through, plus the haze, set so that the
  sea and the clouds match GOES-18's: GOES's blue band at 470 nm stands for the Blue Marble's blue,
  and its red at 640 for its red. Where the Blue Marble's thick clouds stand at 0.9, the haze comes
  to 0.216 in blue, 0.118 in green and 0.069 in red, falling as the wavelength to the power of -3.6,
  close to the -4 of the air's Rayleigh scattering. The air lets through 0.93 of the blue and 0.98 of
  the green, which leaves the clouds a little blue, as GOES sees them.
- The game draws every texel with the same limb law, so the texture keeps the sea's brightness
  against the clouds' as GOES-18 saw it, at those angles.

### Brightness

- The texture's mean luminance is 0.22, the same share of Earth's true brightness as Jupiter's 0.3 is
  of Jupiter's, from NASA's visual geometric albedo of 0.434 and Minnaert's law in green. Its mean
  colour is a bluish grey, sRGB (124, 129, 141) at that luminance.

### City lights

- The night side shows the city lights of NASA's Black Marble of 2016, as the texture's emissive
  map, `realistic_planets_earth_emissive.png`, laid out as the texture is.
- The Black Marble draws the lights over a dark blue picture of the ground and the sea, which isn't
  light the night side gives off. In linear light the ground is always bluer than red, by 1.9 times
  or more, the ratio of Australia's reddest deserts, and the lights are warm, (1, 0.78, 0.61). So a
  texel's red, less its blue over 1.9, is the lights' red, which the ground can't give, and the map
  keeps the lights alone, in their colour. It's scaled down to 4096 by 2048 in linear light first,
  so that a town too small for a texel still lights it by its share.
- Earth's surface function, `earth.glsl`, shows the lights only where the sun has set: they fade in
  from sunset and show whole once the sun is 6 degrees below the horizon, the end of civil twilight.
  The Black Marble is a picture of clear nights, so where the texture shows thick clouds, the lights
  dim, by up to 85%, as the clouds would hide them.
- An emissive map needs the MATERIALS setting under VIDEO, which is on by default.

## The limb

A planet's haze changes how its sunlit limb looks against a plain ball's, mostly brightening it.
The mod's player script, `planets.luau`, draws this with a surface function on each body's
texture: `minnaert.glsl` for the moons, and for each planet and Titan its own shader, such as
`neptune.glsl`, which adds its haze ([The haze](#the-haze)); Saturn's adds the ring's shadow, and
Earth's its city lights. Each takes the law from `limb.glsl`. It needs PER-PIXEL LIGHTING; without it, the planets are drawn
as before.

- The function applies Minnaert's law in full. The part that depends on the sun, mu0^k, sets how
  much of the sun lights the pixel, and the part that depends on the view, mu^(k-1), goes into the
  colour, in linear
  light, with an exponent k for each channel, measured for each planet.
- Neptune's come from the Voyager frames: 0.680 for red, from the orange frames, as Voyager had no
  red filter, 0.712 for green and 0.768 for blue. As k is lowest in red, the limb brightens most in
  red, which makes it paler.
- Jupiter's come from OPAL's maps, whose exponents are 0.850 at 395 nm, 0.950 at 502 and 0.999 at
  631: 0.988 for red, 0.965 for green and 0.905 for blue. Jupiter's limb darkens almost as a plain
  ball's, so its function changes little, and most in blue, a faint bluish haze.
- Uranus's come from OPAL's maps of 2022, whose exponents are 0.85 at 467 nm, 0.80 at 547 and 0.57
  at 657: 0.702 for red, 0.805 for green and 0.85 for blue. Its methane brightens the limb most in
  red, as Neptune's does, so its limb is paler too.
- Saturn's come from OPAL's maps of 2025, whose exponents are 0.40 at 395 nm, 0.65 at 502 and 0.80 at
  631: 0.770 for red, 0.697 for green and 0.540 for blue. Its haze brightens the limb most in blue, so
  its limb turns paler and a little blue.
- Venus's come from six sets of Venus Express's pictures, taken at 365, 513 and 965 nm within a
  minute of each other in July and August 2007, at phase angles of 44 to 55 degrees, and fitted as
  Akatsuki's maps are, with each latitude's own brightness. Their exponents are 0.835 at 365 nm,
  1.081 at 513 and 1.023 at 965: 1.070 for red, 1.077 for green and 0.982 for blue. In visible light
  Venus's limb darkens a little more than a plain ball's, least in blue, so its limb turns a little
  darker and a little blue.
- Titan's come from the same Cassini frames as its haze. Their exponents are 0.876 at 463 nm, 0.897
  at 568 and 0.855 at 647: 0.877 for red, 0.892 for green and 0.876 for blue. Titan's haze brightens
  its limb a little, about as much in each colour, so the limb keeps its colour.
- Earth's come from GOES-18's and GOES-19's pictures of the same moment, from 137 and 75 degrees
  west. Where both saw a place, with the sun and both satellites more than 15 degrees above its
  horizon, they saw the same ground and clouds under the same sun from two angles, so the ratio of
  their brightness follows the two views' angles, once the phase angle is held fixed. One picture
  alone mistakes the scene for the limb: GOES-18's disk is mostly sea in the middle, with land and
  clouds round its edge. Each place counts by its brightness, so the law follows the clouds and the
  land more than the dark sea, whose haze brightens toward the limb. The exponents are 0.750 at 470
  nm and 0.907 at 640: 0.871 for red, 0.815 for green and 0.750 for blue, so the limb turns a little
  blue, as the air's glow does.
- Jupiter's moons' come from the frames that give their colour, each frame's pixels sorted by its
  map's brightness and each group given its own albedo, and each filter's exponent is the median of
  its frames'. Io's are 0.733 at 416 nm, 0.678 at 479, 0.692 at 566 and 0.685 at 591: 0.685 for red,
  0.688 for green and 0.697 for blue. Europa's are 0.669, 0.670 and 0.663, Ganymede's 0.580, 0.561
  and 0.539, and Callisto's 0.578, 0.563 and 0.532. The moons have no air, but their ground scatters
  light as the Moon's dust does, which makes the full Moon look almost evenly bright to its edge, so
  their limbs brighten, Ganymede's and Callisto's the most and a little more in blue.
- Triton's come from its frames in the same way: 0.747 at 416 nm, 0.752 at 479, 0.741 at 566 and
  0.741 at 591, so 0.741 for red, 0.744 for green and 0.750 for blue. Its frost brightens the limb
  about as much in each colour.
- The planets' and Titan's laws were fitted where mu is at least 0.25, and the moons' where it's at
  least 0.2. Nearer the limb, the factor stays as it is there: for Neptune and Uranus at most about
  1.5 times brighter in red, for Jupiter 1.14 in blue, for Saturn 1.89 in blue, for Venus 0.90 in
  green, for Earth 1.41 in blue, for Titan 1.19 in red and blue, for Jupiter's moons from 1.63 for Io
  in blue to 2.12 for Callisto in blue, and for Triton 1.52 in red. The middle of the disk is
  unchanged.
- With k below 1, mu0^k falls off more slowly than the sun's cosine as the sun sinks, so the
  terminator is soft, as a hazy planet's is, and it stands where the sun sets.
- A surface function on the planet only draws on its disk. Each planet's and Titan's adds its haze
  in front of the disk, and draws its haze beyond the disk on a ring of its own
  ([The haze](#the-haze)).

## The haze

Every planet and Titan has a haze, or for Earth its air, drawn by one model, `haze.glsl`, which
each body's shader includes with its own numbers. Each number is physical, so it can be tuned by hand,
and each comes from spacecraft frames or published measurements:

- How much haze there is: its optical depth straight down to the body's sphere, and its scale
  height, the height over which it thins by e. It's cut off 20 scale heights up.
- A detached layer above it, where the body has one, as Titan does: its peak's extinction, its
  height and its width.
- Its colour: its single-scattering albedo, the share of the light it scatters rather than absorbs.
- How it scatters: two Henyey-Greenstein lobes for its particles, each with an asymmetry, from -1
  backward to 1 forward, and a share of the light, and Rayleigh's phase function, the gas's, with the
  rest.
- The phase angle the texture shows the body at, and a matrix that turns the haze's three bands into
  the game's colours, as the texture takes the body's colours and brightness. The bands are a
  camera's filters or three wavelengths, from blue to red; for a body given in red, green and blue,
  the matrix holds just the texture's brightness.

Each pixel's line of sight is followed through the haze, and the sunlight it scatters toward the eye
once is added up, dimmed on its way in by Chapman's integral, so the haze on the night side is lit
only high up, where the sun still reaches it. Beyond the disk the haze is drawn on the ring that
OpenReliant draws behind a planet for its atmosphere (`records.luau`). Over the disk the texture
already holds the body as seen at its own phase angle, haze included, so the haze adds only what its
phase function gives beyond what it gives there: with the sun behind the body, the crescent its
forward scattering lights.

| Body | Optical depth, blue to red | Scale height, km | Albedo | Scattering | Where the numbers come from |
|---|---|---|---|---|---|
| Neptune | 0.0022, 0.0022, 0.0024 | 17, 13, 14 | about 1 | one forward lobe, 0.59 | Voyager 2's frames of the limb at 136 and 152 degrees of phase, in its blue, green and orange filters; the scale height is close to the gas's at the tropopause (Lindal, 1992) |
| Uranus | 0.0046 | 22 | 1 | as Neptune's | Neptune's haze, twice as much of it, as Uranus is hazier (Irwin and others, 2022), with the scale height of its colder, lighter air at the tropopause (Lindal and others, 1987) |
| Saturn | 0.055, 0.050, 0.064 | 40, 29, 30 | 0.38, 1, 0.91 | Rayleigh's, with a narrow forward lobe, 0.96, taking a ninth of the light | Cassini's frames of the limb at 151 to 176 degrees of phase, in its blue, green and red filters |
| Jupiter | 5.8, 5.5, 4.8, down to 1 bar | 19 | 1 | a forward lobe, 0.67 to 0.72, and a faint backward one | a haze near 50 mbar of particles about 0.3 micrometres across, with an optical depth of about a tenth (Zhang and others, 2013; Banfield and others, 1998), thinning with the gas; the lobes from Mie theory |
| Venus | 0.32, 0.21, 0.16 | 3.3 | 1 | two forward lobes, one for each size of droplet, with a little of Rayleigh's | SPICAV IR's occultations: sulphuric acid droplets of 0.12 and 0.84 micrometres, about 500 and 1 per cubic centimetre at 75 km, and the scale height (Luginin and others, 2016); their refractive index (Hansen and Hovenier, 1974); the lobes from Mie theory |
| Titan | 2.55, 0.72, 0.37 | 24, 27, 30 | 1, 0.85, 0.92 | two forward lobes | Cassini's frames from 28 to 164 degrees of phase, in its blue, green and red filters, with a detached layer 288 km above the sphere, about 450 km above the ground (West and others, 2011) |
| Earth | 0.219, 0.107, 0.069 | 8 | 1 | Rayleigh's alone | the air's Rayleigh scattering at the channels' wavelengths (Bucholtz, 1995); the texture holds the haze of dust and droplets low down |

On the giant planets the haze is thin: tens of km on bodies tens of thousands of km across. Beyond the
disk it shows as a fine line along the limb, brightest with the sun behind the planet, as in the
spacecraft's pictures. Titan's haze reaches a fifth of its radius, and is blue at the top, where its
smallest particles scatter blue light the most, and orange below. Earth's air shows as a blue rim,
and as a ring of light round its night side with the sun behind it.

## Making it again

The scripts and the steps to run them are in the collection's
[`sources/realistic-planets`](https://github.com/OpenReliant/openreliant-mods/tree/main/sources/realistic-planets)
folder. A build downloads what each texture is made from, about 80 MB for Neptune, 93 MB for
Jupiter, 3 MB for Uranus, 190 MB for Saturn, 270 MB for Venus, 60 MB for Titan, 1.4 GB for Jupiter's
moons and Triton, and 740 MB for Earth, and makes the same textures again.

## Credits and licences

- Voyager imaging: NASA/JPL-Caltech, in the public domain, from the PDS Ring-Moon Systems Node:
  Voyager 2's frames of Neptune and Triton from its VGISS_8xxx volumes, and Voyager 1's and 2's
  frames of Jupiter's moons from its VGISS_5xxx volumes.
- The global maps of Io, Europa, Ganymede and Callisto: USGS Astrogeology Science Center, from
  NASA's Voyager and Galileo pictures, in the public domain.
- The global colour mosaic of Triton: NASA/JPL and Paul Schenk, Lunar and Planetary Institute, from
  the USGS Astrogeology Science Center, in the public domain.
- NASA's Blue Marble: NASA Goddard Space Flight Center, image by Reto Stöckli (land surface, shallow
  water, clouds), enhancements by Robert Simmon (ocean colour, compositing), from MODIS's data, in
  the public domain.
- NASA's Black Marble of 2016: NASA Earth Observatory images by Joshua Stevens, using Suomi NPP
  VIIRS data from Miguel Román, NASA's Goddard Space Flight Center, in the public domain.
- GOES-18's and GOES-19's pictures: NOAA, in the public domain, from NOAA's open data on Amazon Web
  Services.
- Cassini imaging: NASA/JPL/Space Science Institute, in the public domain, from NASA's Photojournal
  (PIA07782 and PIA11142), and Titan's frames from the PDS Ring-Moon Systems Node's COISS_2053 to
  COISS_2064 volumes and Saturn's from its COISS_2052 and COISS_2080 volumes, calibrated with
  CISSCAL.
- The haze: S. Chapman, "The absorption and ionising effect of monochromatic
  radiation in an atmosphere on a rotating earth, part II: grazing incidence", Proceedings of the
  Physical Society 43 (1931); L. G. Henyey and J. L. Greenstein, "Diffuse radiation in the Galaxy",
  The Astrophysical Journal 93 (1941); for Neptune's tropopause, G. F. Lindal, "The atmosphere of
  Neptune: an analysis of radio occultation data acquired with Voyager 2", The Astronomical Journal
  103 (1992); for Titan's detached layer's height, R. A. West and others, "The evolution of Titan's
  detached haze layer near equinox in 2009", Geophysical Research Letters 38, L06204 (2011),
  [doi:10.1029/2011GL046843](https://doi.org/10.1029/2011GL046843); for Uranus's tropopause, G. F.
  Lindal and others, "The atmosphere of Uranus: results of radio occultation measurements with
  Voyager 2", Journal of Geophysical Research 92 (1987); for Uranus's and Neptune's hazes, P. G. J.
  Irwin and others, "Hazy blue worlds: a holistic aerosol model for Uranus and Neptune, including
  Dark Spots", Journal of Geophysical Research: Planets 127 (2022); and for Earth's air, A. Bucholtz,
  "Rayleigh-scattering calculations for the terrestrial atmosphere", Applied Optics 34 (1995).
- Cassini's map of Titan's surface at 938 nm: NASA/JPL-Caltech/University of Arizona, from NASA's
  Photojournal (PIA22770), free to use with this credit under JPL's image use policy.
- Cassini's global maps of Saturn: L. Li, R. West, X. Jiang and B. Knowles, "Cassini ISS Global Maps
  of Jupiter and Saturn Bundle", NASA Planetary Data System (2023), from the PDS Atmospheres Node;
  X. Wang, L. Li, X. Jiang and R. A. West, "Multi-wavelength global maps of Jupiter and Saturn using
  Cassini imaging system data", Scientific Data 12, 45 (2025).
- Voyager 2's profiles of Saturn's rings: NASA/JPL, in the public domain, from the PDS Ring-Moon
  Systems Node: the photopolarimeter's occultation of delta Scorpii (VG_2801), and M. R. Showalter
  and M. K. Gordon, "VG1/VG2 SR ISS RING PROFILES V1.0" (VG_2810, 2004).
- Hubble OPAL, for Jupiter's calibration and Uranus's and Saturn's maps: this work used data acquired from the
  NASA/ESA HST Space Telescope, associated with OPAL program (PI: Simon, GO13937), CC BY 4.0,
  [doi:10.17909/T9G593](https://doi.org/10.17909/T9G593);
  A. A. Simon, M. H. Wong and G. S. Orton, "First results from the Hubble OPAL program: Jupiter in
  2015", The Astrophysical Journal 812 (2015).
- The spectra of Neptune, Jupiter, Uranus, Saturn and Titan: E. Karkoschka, "Spectrophotometry of the Jovian planets and
  Titan at 300- to 1000-nm wavelength: the methane spectrum", Icarus 111 (1994), from the PDS
  Atmospheres Node.
- Neptune's wind profile: L. A. Sromovsky, S. S. Limaye and P. M. Fry, "Dynamics of Neptune's major
  cloud features", Icarus 105 (1993).
- Akatsuki's ultraviolet maps of Venus: S. Murakami, K. Ogohara, M. Takagi, H. Kashimura, M. Yamada,
  T. Kouyama, T. Horinouchi and T. Imamura, "Venus Climate Orbiter Akatsuki UVI Longitude-Latitude
  Map Data v1.1", JAXA Data Archives and Transmission System (DARTS),
  [doi:10.17597/isas.darts/vco-00016](https://doi.org/10.17597/isas.darts/vco-00016), CC BY 4.0.
- Venus Express's camera, VMC: credit ESA, W. Markiewicz, from ESA's Planetary Science Archive
  (VEX-V-VMC-3-RDR-V3.0), CC BY-NC 3.0 IGO. Only the limb's exponents measured from its pictures
  are in the mod.
- Venus's albedos and phase curves: A. Mallama, B. Krobusek and H. Pavlov, "Comprehensive wide-band
  magnitudes and albedos for the planets, with applications to exo-planets and Planet Nine", Icarus
  282 (2017).
- Jupiter's haze: X. Zhang, R. A. West, D. Banfield and Y. L. Yung, "Stratospheric aerosols on
  Jupiter from Cassini observations", Icarus 226 (2013); D. Banfield and others, "Jupiter's cloud
  structure from Galileo imaging data", Icarus 135 (1998).
- Venus's haze: M. Luginin and others, "Aerosol properties in the upper haze of Venus from SPICAV
  IR data", Icarus 277 (2016), and "Scale heights and detached haze layers in the mesosphere of
  Venus from SPICAV IR data", Icarus (2018); J. E. Hansen and J. W. Hovenier, "Interpretation of the
  polarization of Venus", Journal of the Atmospheric Sciences 31 (1974); Mie theory by S. Prahl's
  miepython.
- The geometric albedos of the Galilean moons, of Triton and of Earth: NASA's Jovian Satellite,
  Neptunian Satellite and Earth Fact Sheets.
- Venus's spectrum considered: A. Payne, G. L. Villanueva and others, "A comprehensive spectroscopic
  reference of the solar system and its application to exoplanet direct imaging", The Planetary
  Science Journal (2025).
- The textures made from the data, the thumbnail and the note are OpenReliant's, shared under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): credit OpenReliant, and for Neptune
  NASA/JPL for the Voyager data, for Jupiter NASA/JPL/Space Science Institute for the Cassini data
  and NASA/ESA Hubble OPAL for its calibration, for Uranus NASA/ESA Hubble OPAL, for Saturn
  NASA/JPL/Space Science Institute for the Cassini data, NASA/ESA Hubble OPAL, and NASA/JPL for the
  Voyager data, for Venus JAXA/ISAS for the Akatsuki data, for Titan NASA/JPL/Space Science
  Institute for the Cassini data and NASA/JPL-Caltech/University of Arizona for the map of its
  surface, for Jupiter's moons NASA/JPL for the Voyager data and the USGS Astrogeology Science
  Center for its maps, for Triton NASA/JPL for the Voyager data and NASA/JPL and the Lunar and
  Planetary Institute for its map, and for Earth NASA Goddard Space Flight Center for the Blue
  Marble, NASA Earth Observatory for the Black Marble and NOAA for the GOES data.
- The spheres, the manifest and the scripts are OpenReliant's, under the Mozilla Public License
  2.0.
