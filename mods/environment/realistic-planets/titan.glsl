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
    vec3(0.007408, 0.00252, 0.001516),
    vec3(24.56, 27.78, 30.63),
    // The detached layer's extinction, radius and width.
    vec3(2.86e-05, 1.371e-05, 9.868e-06),
    vec3(3029.3, 3027.9, 3030.7),
    vec3(44.2, 51.7, 54),
    // The mean phase angle of the frames the texture comes from, 35 degrees.
    -0.816,
    // The albedo, and the phase function's two lobes and their shares, without Rayleigh's.
    vec3(0.74, 0.671, 0.687),
    vec3(0.76, 0.722, 0.729),
    vec3(0.247, 0.595, 0.598),
    vec3(0.62, 1, 1),
    vec3(0.38, 0, 0),
    // The light scattered more than once, fitted to a Monte Carlo of this haze: the beam's chance of
    // each further scattering, and the glow's strength, fall, middle and width.
    vec3(0.347, 0.352, 0.429),
    vec3(0.0184, 0.0278, 0.0212),
    vec3(33.24, 60.49, 2000),
    vec3(-0.241, -0.255, 0.225),
    vec3(0.01, 0.01, 0.0928),
    // Cassini's blue, green and red filters' I/F to the game's colours.
    mat3(-0.14988, 0.21081, 0.69685, 0.27673, 0.35667, -0.03369, 0.35095, -0.00266, -0.00834),
    // A quarter of the haze's light blooms, as the bloom would spread the bright haze of a backlit
    // Titan well past what Cassini saw.
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, titanHaze);
}
