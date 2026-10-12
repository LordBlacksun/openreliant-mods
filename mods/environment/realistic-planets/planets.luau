-- Realistic Planets: lights each body to match its measured photometry with Minnaert's law
-- (minnaert.glsl), draws the haze or air of the planets and Titan (haze.glsl, included by each
-- body's shader), shades Saturn with its ring, and shows Earth's city lights at night. This is a
-- player script, so it runs for the whole game. The functions need PER-PIXEL LIGHTING.
-- records.luau sets how the bodies turn and lean, and which rings their haze is drawn on.

local shaders = require("openreliant.shaders")

-- The smallest cosine of the view angle that the planets' and Titan's exponents were fitted to,
-- and the one for the other moons. Closer to the limb, the law keeps the value it has there.
local PLANET_LEAST_COSINE = 0.25
local MOON_LEAST_COSINE = 0.2

-- Registers a body's surface function, which draws its texture `realistic_planets_<name>` with
-- Minnaert's exponents for red, green and blue, `k`. With `haze`, it also registers the function
-- `<name>_haze`, which draws the haze beyond the disk: the same shader, given no parameters.
local function register(name, shader, k, least_cosine, haze)
    shaders.register_surface({
        name = name,
        shader = shader,
        textures = { "realistic_planets_" .. name },
        parameters = { k[1], k[2], k[3], least_cosine },
    })
    if haze then
        shaders.register_surface({ name = name .. "_haze", shader = shader })
    end
end

-- Each planet's exponents are measured in a few filters and taken at the wavelengths of the red,
-- green and blue channels for that planet's spectrum. The mod's README gives the details.

-- Neptune: fitted to Voyager 2's orange, green and blue frames (neptune-voyager-map.pdf, Table 2).
register("neptune", "neptune.glsl", { 0.680, 0.712, 0.768 }, PLANET_LEAST_COSINE, true)

-- Jupiter: Hubble's OPAL maps of January 2015 (0.850 at 395 nm, 0.950 at 502 and 0.999 at 631),
-- at 602, 541 and 454 nm.
register("jupiter", "jupiter.glsl", { 0.988, 0.965, 0.905 }, PLANET_LEAST_COSINE, true)

-- Uranus: Hubble's OPAL maps of November 2022 (0.85 at 467 nm, 0.80 at 547 and 0.57 at 657), at
-- 594, 539 and 453 nm, with blue using the value at 467.
register("uranus", "uranus.glsl", { 0.702, 0.805, 0.850 }, PLANET_LEAST_COSINE, true)

-- Saturn: Hubble's OPAL maps of August 2025 (0.40 at 395 nm, 0.65 at 502 and 0.80 at 631), at 605,
-- 542 and 455 nm.
register("saturn", "saturn.glsl", { 0.770, 0.697, 0.540 }, PLANET_LEAST_COSINE, true)

-- Venus: Venus Express's pictures (0.835 at 365 nm, 1.081 at 513 and 1.023 at 965), at 602, 541
-- and 453 nm.
register("venus", "venus.glsl", { 1.070, 1.077, 0.982 }, PLANET_LEAST_COSINE, true)

-- Earth: GOES-18's and GOES-19's pictures of the same moment, from 137 and 75 degrees west (0.750
-- at 470 nm and 0.907 at 640), at 601, 540 and 452 nm for a grey spectrum, with blue using the
-- value at 470. earth.glsl also draws its city lights on the night side.
register("earth", "earth.glsl", { 0.871, 0.815, 0.750 }, PLANET_LEAST_COSINE, true)

-- Titan: Cassini's frames of 2010 (0.876 at 463 nm, 0.897 at 568 and 0.855 at 647), at 606, 544
-- and 455 nm.
register("titan", "titan.glsl", { 0.877, 0.892, 0.876 }, PLANET_LEAST_COSINE, true)

-- Jupiter's moons: Voyager's frames of 1979, at about 604, 542 and 455 nm for each moon's
-- spectrum.
-- Io: 0.733 at 416 nm, 0.678 at 479, 0.692 at 566 and 0.685 at 591.
register("io", "minnaert.glsl", { 0.685, 0.688, 0.697 }, MOON_LEAST_COSINE)
-- Europa: 0.660 at 416 nm, 0.664 at 479, 0.673 at 566 and 0.669 at 591.
register("europa", "minnaert.glsl", { 0.669, 0.670, 0.663 }, MOON_LEAST_COSINE)
-- Ganymede: 0.525 at 416 nm, 0.548 at 479, 0.566 at 566 and 0.580 at 591.
register("ganymede", "minnaert.glsl", { 0.580, 0.561, 0.539 }, MOON_LEAST_COSINE)
-- Callisto: 0.517 at 416 nm, 0.542 at 479, 0.571 at 566 and 0.578 at 591.
register("callisto", "minnaert.glsl", { 0.578, 0.563, 0.532 }, MOON_LEAST_COSINE)

-- Triton: Voyager 2's frames of 1989 (0.747 at 416 nm, 0.752 at 479, 0.741 at 566 and 0.741 at
-- 591), at 601, 541 and 453 nm.
register("triton", "minnaert.glsl", { 0.741, 0.744, 0.750 }, MOON_LEAST_COSINE)

-- Saturn's ring, drawn see-through (rings.glsl). The sun lights it on one side and shines through
-- it on the other, and Saturn's shadow falls on it. The parameters are the smallest cosine of the
-- view angle, so that it stays finite edge on (about 1.1 degrees), and the encoded brightness of
-- the planet behind it that its blending is fitted to.
shaders.register_surface({
    name = "saturn_rings",
    shader = "rings.glsl",
    textures = { "realistic_planets_saturn_rings" },
    see_through = true,
    parameters = { 0, 0.02, 0.5 },
})
