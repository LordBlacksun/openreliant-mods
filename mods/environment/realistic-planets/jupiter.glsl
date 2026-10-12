// Realistic Planets (planets.luau): Jupiter and its stratospheric haze (haze.glsl), from what was
// measured of it. sources/realistic-planets/jupiter/haze.py works the numbers below out at 450, 550
// and 650 nm with Mie theory, and prints them.

#include "haze.glsl"

const RealisticPlanetsHaze jupiterHaze = RealisticPlanetsHaze(
    // The spheroid's equatorial radius in the game, Jupiter's at 1 bar, and its polar radius's share
    // of it. Jupiter's model holds the spheroid alone.
    71492.0,
    0.9351,
    71492.0,
    // The radius the haze's extinction is given at, about where 50 mbar lies, and the radius it is cut
    // off at.
    71562.0,
    71912.0,
    // The haze's extinction, from its optical depth and its particles' cross-sections, and the gas's
    // scale height near 50 mbar.
    vec3(0.007674, 0.007219, 0.006313),
    vec3(19, 19, 19),
    // No detached layer.
    vec3(0, 0, 0),
    vec3(71492, 71492, 71492),
    vec3(1, 1, 1),
    // The maps take the light's angle out, so the texture shows Jupiter as from the sun.
    -1.000,
    // The albedo, and the phase function: two Henyey-Greenstein lobes and Rayleigh's, fitted to Mie
    // theory's.
    vec3(1, 1, 1),
    vec3(0.719, 0.693, 0.664),
    vec3(-0.624, -0.695, 0.664),
    vec3(0.978, 0.992, 0.991),
    vec3(0.0218, 0.00823, 0.00346),
    // The light scattered more than once isn't estimated for Jupiter: no beam and no glow.
    vec3(0, 0, 0),
    vec3(0, 0, 0),
    vec3(1, 1, 1),
    vec3(0, 0, 0),
    vec3(1, 1, 1),
    // The haze's I/F at 450, 550 and 650 nm to the game's colours.
    mat3(-0.07895, 0.08304, 0.74668, 0.17935, 0.50883, 0.00725, 0.50345, 0.02853, -0.01705),
    // A quarter of the haze's light blooms, as for the other bodies.
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, jupiterHaze);
}
