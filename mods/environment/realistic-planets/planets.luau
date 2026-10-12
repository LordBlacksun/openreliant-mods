-- Realistic Planets: lights each body as its photometry was measured, with Minnaert's law
-- (minnaert.glsl), Saturn shaded by its ring (saturn.glsl), Earth with its city lights at night
-- (earth.glsl) and Titan with its haze (titan.glsl). This is a player script: it runs for the whole
-- game. The functions need PER-PIXEL LIGHTING. How the bodies turn and lean, and which ring Titan's
-- haze is drawn on, is in records.luau.

local shaders = require("openreliant.shaders")

-- Neptune: Minnaert's exponents fitted to Voyager 2's orange, green and blue frames, for the red,
-- green and blue channels, and the least cosine of the view they were fitted at
-- (neptune-voyager-map.pdf, Table 2).
shaders.register_surface({
    name = "neptune",
    shader = "minnaert.glsl",
    textures = { "realistic_planets_neptune" },
    parameters = { 0.680, 0.712, 0.768, 0.25 },
})

-- Jupiter: the exponents of Hubble's OPAL maps of January 2015 (0.850 at 395 nm, 0.950 at 502 and
-- 0.999 at 631), at the red, green and blue channels' wavelengths for Jupiter's spectrum (602, 541
-- and 454 nm), and the same least cosine.
shaders.register_surface({
    name = "jupiter",
    shader = "minnaert.glsl",
    textures = { "realistic_planets_jupiter" },
    parameters = { 0.988, 0.965, 0.905, 0.25 },
})

-- Uranus: the exponents of Hubble's OPAL maps of November 2022 (0.85 at 467 nm, 0.80 at 547 and 0.57
-- at 657), at the red, green and blue channels' wavelengths for Uranus's spectrum (594, 539 and 453
-- nm, the blue taking 467's), and the same least cosine.
shaders.register_surface({
    name = "uranus",
    shader = "minnaert.glsl",
    textures = { "realistic_planets_uranus" },
    parameters = { 0.702, 0.805, 0.850, 0.25 },
})

-- Saturn: the exponents of Hubble's OPAL maps of August 2025 (0.40 at 395 nm, 0.65 at 502 and 0.80
-- at 631), at the red, green and blue channels' wavelengths for Saturn's spectrum (605, 542 and 455
-- nm), and the same least cosine.
shaders.register_surface({
    name = "saturn",
    shader = "saturn.glsl",
    textures = { "realistic_planets_saturn" },
    parameters = { 0.770, 0.697, 0.540, 0.25 },
})

-- Venus: the exponents of Venus Express's pictures (0.835 at 365 nm, 1.081 at 513 and 1.023 at 965),
-- at the red, green and blue channels' wavelengths for Venus's spectrum (602, 541 and 453 nm), and the
-- same least cosine.
shaders.register_surface({
    name = "venus",
    shader = "minnaert.glsl",
    textures = { "realistic_planets_venus" },
    parameters = { 1.070, 1.077, 0.982, 0.25 },
})

-- Earth: the exponents of GOES-18's and GOES-19's pictures of the same moment, from 137 and 75 degrees
-- west (0.750 at 470 nm and 0.907 at 640), at the red, green and blue channels' wavelengths for a grey
-- spectrum (601, 540 and 452 nm, the blue taking 470's), and the same least cosine; and its city
-- lights on its night side.
shaders.register_surface({
    name = "earth",
    shader = "earth.glsl",
    textures = { "realistic_planets_earth" },
    parameters = { 0.871, 0.815, 0.750, 0.25 },
})

-- Titan: the exponents of Cassini's frames of 2010 (0.876 at 463 nm, 0.897 at 568 and 0.855 at 647),
-- at the red, green and blue channels' wavelengths for Titan's spectrum (606, 544 and 455 nm), and the
-- same least cosine; and its haze in front of the disk.
shaders.register_surface({
    name = "titan",
    shader = "titan.glsl",
    textures = { "realistic_planets_titan" },
    parameters = { 0.877, 0.892, 0.876, 0.25 },
})

-- Titan's haze beyond its disk, which titan.glsl draws where it is given no parameters: single
-- scattering of sunlight in its main haze and its detached layer, fitted to Cassini's frames from 28
-- to 164 degrees of phase by the collection's sources/realistic-planets/titan/haze.py. records.luau
-- gives Titan the ring it draws on.
shaders.register_surface({
    name = "titan_haze",
    shader = "titan.glsl",
})

-- Jupiter's moons: the exponents of Voyager's frames of 1979, at the red, green and blue channels'
-- wavelengths for each moon's spectrum (about 604, 542 and 455 nm), and the least cosine of the view
-- they were fitted at. Io: 0.733 at 416 nm, 0.678 at 479, 0.692 at 566 and 0.685 at 591.
shaders.register_surface({
    name = "io",
    shader = "minnaert.glsl",
    textures = { "realistic_planets_io" },
    parameters = { 0.685, 0.688, 0.697, 0.2 },
})

-- Europa: 0.660 at 416 nm, 0.664 at 479, 0.673 at 566 and 0.669 at 591.
shaders.register_surface({
    name = "europa",
    shader = "minnaert.glsl",
    textures = { "realistic_planets_europa" },
    parameters = { 0.669, 0.670, 0.663, 0.2 },
})

-- Ganymede: 0.525 at 416 nm, 0.548 at 479, 0.566 at 566 and 0.580 at 591.
shaders.register_surface({
    name = "ganymede",
    shader = "minnaert.glsl",
    textures = { "realistic_planets_ganymede" },
    parameters = { 0.580, 0.561, 0.539, 0.2 },
})

-- Callisto: 0.517 at 416 nm, 0.542 at 479, 0.571 at 566 and 0.578 at 591.
shaders.register_surface({
    name = "callisto",
    shader = "minnaert.glsl",
    textures = { "realistic_planets_callisto" },
    parameters = { 0.578, 0.563, 0.532, 0.2 },
})

-- Triton: the exponents of Voyager 2's frames of 1989, 0.747 at 416 nm, 0.752 at 479, 0.741 at 566 and
-- 0.741 at 591, at the channels' wavelengths for its spectrum (601, 541 and 453 nm), and the same
-- least cosine as Jupiter's moons.
shaders.register_surface({
    name = "triton",
    shader = "minnaert.glsl",
    textures = { "realistic_planets_triton" },
    parameters = { 0.741, 0.744, 0.750, 0.2 },
})

-- Saturn's ring, see-through (rings.glsl): lit by the sun on the side it shines on and through the
-- ring on the other, shaded where Saturn stands between it and the sun, seen at least 1.1 degrees
-- from edge on, and blended to suit the planet's lit side behind it, about 0.5 encoded.
shaders.register_surface({
    name = "saturn_rings",
    shader = "rings.glsl",
    textures = { "realistic_planets_saturn_rings" },
    see_through = true,
    parameters = { 0, 0.02, 0.5 },
})
