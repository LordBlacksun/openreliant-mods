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
