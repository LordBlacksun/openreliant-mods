-- Realistic Planets: draws each planet's limb as its photometry was measured, with Minnaert's law
-- (minnaert.glsl). This is a player script: it runs for the whole game. The functions need
-- PER-PIXEL LIGHTING.

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
