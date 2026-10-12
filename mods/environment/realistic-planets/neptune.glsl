// Realistic Planets (planets.luau): Neptune and its haze (haze.glsl), as Voyager 2's frames of 1989
// show it at 136 and 152 degrees of phase. sources/realistic-planets/neptune/haze.py fits the
// numbers below, in Voyager's blue, green and orange filters, and prints them. The haze stands for
// the gas and the haze together.

#include "haze.glsl"

const RealisticPlanetsHaze neptuneHaze = RealisticPlanetsHaze(
    // The sphere's radius in the game, Neptune's equatorial radius: the haze's edge in each filter,
    // where the texture's disk ends.
    24764.0,
    // The radius the haze's extinction is given at, 100 km above the edge, and the radius it is cut
    // off at, 300 km above it.
    24864.0,
    25064.0,
    // The haze's extinction and scale height.
    vec3(4.49e-07, 1.075e-07, 1.284e-07),
    vec3(16.18, 12.75, 12.95),
    // No detached layer.
    vec3(0, 0, 0),
    vec3(24764, 24764, 24764),
    vec3(1, 1, 1),
    // The mean phase angle of the frames the texture comes from, 15 degrees.
    -0.966,
    // The albedo, and the phase function: one Henyey-Greenstein lobe, without Rayleigh's.
    vec3(1, 1, 0.998),
    vec3(0.609, 0.609, 0.609),
    vec3(0, 0, 0),
    vec3(1, 1, 1),
    vec3(0, 0, 0),
    // Voyager's blue, green and orange filters' I/F to the game's colours.
    mat3(-0.20353, 0.25230, 1.42995, -0.05585, 0.68837, -0.06105, 1.13900, 0.09700, -0.04382),
    // A quarter of the haze's light blooms, as for Titan's.
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, neptuneHaze);
}
