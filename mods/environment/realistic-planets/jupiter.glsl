// Realistic Planets (planets.luau): Jupiter and its haze (haze.glsl): a haze of small particles
// above the clouds, about 19 km a scale height, scattering forward, with a faint backward lobe. The
// mod's README gives the numbers' sources.

#include "haze.glsl"

const RealisticPlanetsHaze jupiterHaze = RealisticPlanetsHaze(
    // Jupiter's equatorial radius at 1 bar, km, and its polar radius's share of it.
    71492.0, 0.9351, 71492.0,
    // The haze's optical depth down to 1 bar, and its scale height, at 450, 550 and 650 nm.
    vec3(5.8, 5.5, 4.8),
    vec3(19.0),
    // No detached layer.
    vec3(0.0), 0.0, 1.0,
    // Its albedo, and a forward lobe with a faint backward one.
    vec3(1.0),
    vec3(0.721, 0.694, 0.668), vec3(-0.662, -0.774, -0.867), vec3(0.978, 0.993, 0.998), vec3(0.0217, 0.0071, 0.0019),
    // The texture shows Jupiter as from the sun; the wavelengths to the texture's colours, and a
    // quarter of the haze's light blooming.
    0.0,
    mat3(-0.07895, 0.08304, 0.59734, 0.17935, 0.50883, 0.00580, 0.50345, 0.02853, -0.01364),
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, jupiterHaze);
}
