-- Realistic Planets: how each body turns and leans, in OpenReliant's table of planets
-- (records.planets), Neptune's and Titan's haze beyond their disks, and Earth made a planet, so that
-- the sun alone lights it, as it lights the others. This is a load script: it runs once, as
-- OpenReliant starts.

local records = require("openreliant.records")

-- How many times faster than in reality the bodies turn. At 60 an hour passes in a minute, and
-- Jupiter, the fastest, turns once every ten minutes.
local TIME_SCALE = 60

-- Each body's sidereal day in hours, negative where it turns westward, and how far its north pole
-- leans from the pole of its orbit, in degrees, from NASA's planetary fact sheets. North is the one
-- the International Astronomical Union names, on the north side of the solar system, which is at
-- the top of each body's texture: so Venus and Uranus lean 2.64 and 82.23 degrees and turn
-- westward. Venus's map shows its cloud tops, which turn westward once in about five days, as
-- Akatsuki's maps show them, far faster than the ground under them. A moon turns once an orbit and
-- leans as its planet does, since it orbits in the plane of its planet's equator. Triton's north
-- pole stands about 30 degrees from the solar system's, and it turns westward, as it orbits
-- Neptune.
local BODIES = {
    neptune = { day = 16.11, tilt = 28.32, haze = { surface = "neptune_haze", inner = 0.98, outer = 1.013 } },
    triton = { day = -141.04, tilt = 30 },
    uranus = { day = -17.24, tilt = 82.23 },
    saturn = { day = 10.656, tilt = 26.73 },
    titan = { day = 382.69, tilt = 26.73, haze = { surface = "titan_haze", inner = 0.98, outer = 1.25 } },
    jupiter = { day = 9.925, tilt = 3.13 },
    europa = { day = 85.23, tilt = 3.13 },
    ganymede = { day = 171.71, tilt = 3.13 },
    io = { day = 42.46, tilt = 3.13 },
    calisto = { day = 400.54, tilt = 3.13 },
    venus = { day = -120, tilt = 2.64 },
    earth = { day = 23.934, tilt = 23.44 },
}

-- Which way each north pole leans: toward the body's left, -X, as the mission places it. The game has
-- no orbits to take a season from, and this way, from where the player starts each of the game's
-- missions with Saturn, its ring shows open, by 8 to 37 degrees, where unleaned it's often edge on.
local TILT_TOWARD = -math.pi / 2

-- Sets a planet's spin and lean from its body. The band the game draws over the rim of Neptune,
-- Uranus, Jupiter and Venus is left out, as each body's limb law, fitted to its measured photometry,
-- already gives the rim its light. A body with a haze beyond its disk has it drawn by its surface
-- function (planets.luau) on a ring from `inner` to `outer` times its radius: Neptune's haze
-- reaches 300 km above its edge, about a hundredth of its radius, and Titan's about 700 km, a
-- quarter.
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
