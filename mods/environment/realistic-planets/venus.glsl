// Realistic Planets (planets.luau): Venus and its upper haze (haze.glsl), as Venus Express measured
// it. sources/realistic-planets/venus/haze.py works the numbers below out at 450, 550 and 650 nm
// from SPICAV IR's solar occultations and Mie theory, and prints them.

#include "haze.glsl"

const RealisticPlanetsHaze venusHaze = RealisticPlanetsHaze(
    // The sphere's radius in the game, Venus's cloud tops, 70 km up: where the texture's disk ends.
    // Venus is round, and its model holds the sphere alone.
    6121.8,
    1.0000,
    6121.8,
    // The radius the haze's extinction is given at, 75 km up, where the droplets' numbers were
    // measured, and the radius it is cut off at, 60 km above the cloud tops.
    6126.8,
    6181.8,
    // The haze's extinction, from the droplets' numbers and cross-sections, and the aerosol scale
    // height measured.
    vec3(0.02154, 0.01399, 0.0104),
    vec3(3.3, 3.3, 3.3),
    // No detached layer.
    vec3(0, 0, 0),
    vec3(6121.8, 6121.8, 6121.8),
    vec3(1, 1, 1),
    // The phase angle whose colour the texture takes, 45 degrees.
    -0.707,
    // The albedo of droplets of sulphuric acid, and their phase function as two Henyey-Greenstein
    // lobes and Rayleigh's, fitted to Mie theory's.
    vec3(1, 1, 1),
    vec3(0.897, 0.871, 0.842),
    vec3(0.559, 0.491, 0.474),
    vec3(0.103, 0.178, 0.281),
    vec3(0.881, 0.743, 0.56),
    // The light scattered more than once isn't estimated for Venus: no beam and no glow.
    vec3(0, 0, 0),
    vec3(0, 0, 0),
    vec3(1, 1, 1),
    vec3(0, 0, 0),
    vec3(1, 1, 1),
    // The haze's I/F at 450, 550 and 650 nm to the game's colours.
    mat3(-0.07305, 0.07647, 0.59359, 0.17774, 0.50200, 0.00681, 0.49614, 0.02599, -0.01317),
    // A quarter of the haze's light blooms, as for the other bodies.
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, venusHaze);
}
