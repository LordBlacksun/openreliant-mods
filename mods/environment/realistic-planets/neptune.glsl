// Realistic Planets (planets.luau): Neptune and its haze (haze.glsl), as Voyager 2's frames show it at
// 136 and 152 degrees of phase: a thin haze above the clouds, about 15 km a scale height, much the
// same in every colour, scattering forward. The mod's README gives the sources of the numbers.

#include "haze.glsl"

const RealisticPlanetsHaze neptuneHaze = RealisticPlanetsHaze(
    // Neptune's equatorial radius at 1 bar, km. The game's Neptune is round.
    24764.0, 1.0, 24764.0,
    // The haze's optical depth and scale heights, in Voyager's blue, green and orange filters.
    vec3(0.0022, 0.0022, 0.0024),
    vec3(17.1, 13.4, 13.6),
    // No detached layer.
    vec3(0.0), 0.0, 1.0,
    // Its albedo, and one forward lobe.
    vec3(1.0, 0.99, 1.0),
    vec3(0.59), vec3(0.0), vec3(1.0), vec3(0.0),
    // The cloud tops' forward light, its strength and lobe: about 2.5 times the crescent's light at
    // 160 degrees, and next to nothing at 133, as Voyager 2's frames show it.
    0.18, 0.8,
    // The mean phase angle of the texture's frames, the filters to the texture's colours, and the
    // share of the haze's light that blooms.
    15.0,
    mat3(-0.20353, 0.25230, 1.14396, -0.05585, 0.68837, -0.04884, 1.13900, 0.09700, -0.03506),
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, neptuneHaze);
}
