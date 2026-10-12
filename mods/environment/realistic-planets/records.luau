-- Realistic Planets: sets how each body turns and leans in OpenReliant's table of planets
-- (records.planets), makes the planets' light white, sets the rings that the haze beyond the disk
-- of each planet and Titan is drawn on, and makes Earth a planet, so that only the sun lights it,
-- like the others. This is a load script, so it runs once as OpenReliant starts.

local records = require("openreliant.records")

-- The light on the planets, white, since the textures hold each body's true colour. The game's key
-- lights, (1, 1, 0.8), would turn them yellow. Only the planets and their atmospheres use this light.
records.planet_light = vector.create(1, 1, 1)

-- How many times faster than in reality the bodies turn. At 60 an hour passes in a minute, and
-- Jupiter, the fastest, turns once every ten minutes.
local TIME_SCALE = 60

-- Each body's sidereal day in hours, negative if it turns westward, and how far its north pole
-- leans from the pole of its orbit, in degrees, from NASA's planetary fact sheets. North is the
-- pole the International Astronomical Union calls north, on the north side of the solar system,
-- and it is at the top of each body's texture. So Venus and Uranus lean 2.64 and 82.23 degrees and
-- turn westward. Venus's map shows its cloud tops, which turn westward once in about five days
-- according to Akatsuki's maps, much faster than the ground under them. A moon turns once per
-- orbit and leans like its planet, since it orbits in the plane of the planet's equator. Triton's
-- north pole is about 30 degrees from the solar system's, and it turns westward, the same way it
-- orbits Neptune.
local BODIES = {
    neptune = { day = 16.11, tilt = 28.32, haze = { surface = "neptune_haze", inner = 0.98, outer = 1.014 } },
    triton = { day = -141.04, tilt = 30 },
    uranus = { day = -17.24, tilt = 82.23, haze = { surface = "uranus_haze", inner = 0.98, outer = 1.018 } },
    saturn = { day = 10.656, tilt = 26.73, haze = { surface = "saturn_haze", inner = 0.378, outer = 0.435 } },
    titan = { day = 382.69, tilt = 26.73, haze = { surface = "titan_haze", inner = 0.98, outer = 1.25 } },
    jupiter = { day = 9.925, tilt = 3.13, haze = { surface = "jupiter_haze", inner = 0.92, outer = 1.008 } },
    europa = { day = 85.23, tilt = 3.13 },
    ganymede = { day = 171.71, tilt = 3.13 },
    io = { day = 42.46, tilt = 3.13 },
    calisto = { day = 400.54, tilt = 3.13 },
    venus = { day = -120, tilt = 2.64, haze = { surface = "venus_haze", inner = 0.98, outer = 1.012 } },
    earth = { day = 23.934, tilt = 23.44, haze = { surface = "earth_haze", inner = 0.98, outer = 1.026 } },
}

-- Which way each north pole leans: toward the body's left, -X, in the orientation the mission gives
-- it. The game has no orbits to take a season from. With this lean, Saturn's ring is open by 8 to
-- 37 degrees from where the player starts in each mission with Saturn; without it, the ring is
-- often edge on.
local TILT_TOWARD = -math.pi / 2

-- Sets a planet's spin and lean from its body. It removes the band the game draws over the rim of
-- Neptune, Uranus, Jupiter and Venus, since each body's limb law, fitted to its measured
-- photometry, already lights the rim. A body's haze beyond its disk is drawn by its surface
-- function (planets.luau) on a ring from `inner` to `outer` times its radius. The ring reaches
-- past where haze.glsl cuts the haze off, 20 scale heights above the edge: about 340 km for
-- Neptune, 440 km for Uranus, 380 km for Jupiter, 70 km for Venus and 160 km for Earth, one or two
-- hundredths of their radii, and 600 km for Titan, a fifth of its radius. OpenReliant uses half
-- the widest span of a planet's model as its radius, which for Saturn is the outer edge of its
-- rings, 141,000 km. So Saturn's haze ring runs from just inside its polar edge, 54,364 km, to
-- 1,000 km above its equator, beyond the 810 km that its haze reaches.
local function apply(planet, body)
    planet.spin = 2 * math.pi * TIME_SCALE / (body.day * 3600)
    planet.tilt = math.rad(body.tilt)
    planet.tilt_toward = TILT_TOWARD
    planet.atmosphere_color = nil
    if body.haze then
        planet.atmosphere_surface = body.haze.surface
        planet.atmosphere_inner = body.haze.inner
        planet.atmosphere_outer = body.haze.outer
    end
end

local planets = records.planets
for n = 1, #planets do
    local planet = planets[n]
    local body = BODIES[string.match(planet.type, "^(%a+)_[hl][io]$") or ""]
    if body then
        apply(planet, body)
    end
end
planets[#planets + 1] = { type = "earth" }
apply(planets[#planets], BODIES.earth)
