// Realistic Planets (planets.luau): Venus and its upper haze (haze.glsl), above the cloud tops: small
// and micron-sized droplets of sulphuric acid, about 3 km a scale height, scattering strongly forward
// and absorbing next to nothing. The mod's README gives the sources of the numbers.

#include "haze.glsl"

const RealisticPlanetsHaze venusHaze = RealisticPlanetsHaze(
    // Venus's radius at its cloud tops, km, its solid radius and 70 km. Venus is round.
    6121.8, 1.0, 6121.8,
    // The haze's optical depth and scale height, at 450, 550 and 650 nm.
    vec3(0.323, 0.210, 0.156),
    vec3(3.3),
    // No detached layer.
    vec3(0.0), 0.0, 1.0,
    // Its albedo, and two forward lobes, the droplets' two sizes, with a little of Rayleigh's.
    vec3(1.0),
    vec3(0.897, 0.874, 0.848), vec3(0.542, 0.474, 0.48), vec3(0.104, 0.172, 0.259), vec3(0.896, 0.779, 0.588),
    // The cloud tops' forward light, its strength and lobe: Venus's brightness by phase angle
    // (Mallama and others, 2017) within about a tenth from 90 to 160 degrees.
    0.45, 0.6,
    // The phase angle of the texture's colour, the wavelengths to the texture's colours, and the
    // share of the haze's light that blooms.
    45.0,
    mat3(-0.07305, 0.07647, 0.59359, 0.17774, 0.50200, 0.00681, 0.49614, 0.02599, -0.01317),
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, venusHaze);
}
