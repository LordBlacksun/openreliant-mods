// Realistic Planets (planets.luau): Neptune and its haze (haze.glsl), as Voyager 2's frames of 1989
// show it at 136 and 152 degrees of phase. sources/realistic-planets/neptune/haze.py fits the
// numbers below, in Voyager's blue, green and orange filters, and prints them. The haze stands for
// the gas and the haze together.

#include "haze.glsl"

const RealisticPlanetsHaze neptuneHaze = RealisticPlanetsHaze(
    // The sphere's radius in the game, Neptune's equatorial radius: the haze's edge in each filter,
    // where the texture's disk ends. The game's Neptune is round, and its model holds the sphere
    // alone.
    24764.0,
    1.0,
    24764.0,
    // The radius the haze's extinction is given at, 100 km above the edge, and the radius it is cut
    // off at, 300 km above it.
    24864.0,
    25064.0,
    // The haze's extinction and scale height.
    vec3(3.717e-07, 9.532e-08, 1.097e-07),
    vec3(17.06, 13.4, 13.57),
    // No detached layer.
    vec3(0, 0, 0),
    vec3(24764, 24764, 24764),
    vec3(1, 1, 1),
    // The mean phase angle of the frames the texture comes from, 15 degrees.
    -0.966,
    // The albedo, and the phase function: one Henyey-Greenstein lobe, and Rayleigh's with a
    // thousandth of the light.
    vec3(1, 0.987, 0.999),
    vec3(0.591, 0.591, 0.591),
    vec3(0, 0, 0),
    vec3(0.999, 0.999, 0.999),
    vec3(0, 0, 0),
    // The light scattered more than once, fitted to a Monte Carlo of this haze: the beam's chance of
    // each further scattering, and the glow's strength, fall, middle and width.
    vec3(0.695, 0.538, 0.522),
    vec3(1.05, 0.516, 0.586),
    vec3(864.7, 2000, 2000),
    vec3(0.499, 0.46, 0.463),
    vec3(0.119, 0.115, 0.116),
    // Voyager's blue, green and orange filters' I/F to the game's colours.
    mat3(-0.20353, 0.25230, 1.14396, -0.05585, 0.68837, -0.04884, 1.13900, 0.09700, -0.03506),
    // A quarter of the haze's light blooms, as for Titan's.
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, neptuneHaze);
}
