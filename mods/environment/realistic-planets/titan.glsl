// Realistic Planets (planets.luau): Titan and its haze (haze.glsl), as Cassini's frames of 2009 and
// 2010 show it from 28 to 164 degrees of phase. sources/realistic-planets/titan/haze.py fits the
// numbers below, in Cassini's blue, green and red filters, and prints them.

#include "haze.glsl"

const RealisticPlanetsHaze titanHaze = RealisticPlanetsHaze(
    // The sphere's radius in the game: the haze's edge in green, where the texture's disk ends.
    2741.0,
    // The radius the main haze's extinction is given at, 100 km above 2710 km, and the radius the
    // haze is cut off at, 700 km above it.
    2810.0,
    3410.0,
    // The main haze's extinction and scale height.
    vec3(0.006077, 0.002138, 0.001237),
    vec3(24.2, 27.49, 30.09),
    // The detached layer's extinction, radius and width.
    vec3(2.249e-05, 1.111e-05, 7.7e-06),
    vec3(3028.6, 3028.8, 3031),
    vec3(44.9, 52, 55.2),
    // The mean phase angle of the frames the texture comes from, 35 degrees.
    -0.816,
    // The albedo, and the phase function's two lobes and their shares, without Rayleigh's.
    vec3(1, 0.854, 0.923),
    vec3(0.758, 0.682, 0.689),
    vec3(0.232, 0.594, 0.594),
    vec3(0.556, 1, 1),
    vec3(0.444, 0, 0),
    // Cassini's blue, green and red filters' I/F to the game's colours.
    mat3(-0.14988, 0.21081, 0.69685, 0.27673, 0.35667, -0.03369, 0.35095, -0.00266, -0.00834),
    // A quarter of the haze's light blooms, as the bloom would spread the bright haze of a backlit
    // Titan well past what Cassini saw.
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, titanHaze);
}
