// Realistic Planets (planets.luau): Uranus and its haze (haze.glsl): a thin haze above the clouds,
// as Neptune's, about twice as much of it, as Uranus is hazier, and higher, as its colder, lighter
// atmosphere is, about 22 km a scale height. The mod's README gives the numbers' sources.

#include "haze.glsl"

const RealisticPlanetsHaze uranusHaze = RealisticPlanetsHaze(
    // Uranus's equatorial radius at 1 bar, km, and its polar radius's share of it.
    25559.0, 0.9771, 25559.0,
    // The haze's optical depth and scale height, the same in blue, green and red.
    vec3(0.0046),
    vec3(22.0),
    // No detached layer.
    vec3(0.0), 0.0, 1.0,
    // Its albedo, and one forward lobe, as Neptune's.
    vec3(1.0),
    vec3(0.59), vec3(0.0), vec3(1.0), vec3(0.0),
    // The cloud tops' forward light, its strength and lobe: about twice the crescent's light at 147
    // degrees, as Voyager 2's frames show it, with Neptune's lobe.
    0.34, 0.8,
    // The texture shows Uranus as from the sun; blue, green and red to the texture's channels, at
    // the texture's brightness, and a quarter of the haze's light blooming.
    0.0,
    mat3(0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0),
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, uranusHaze);
}
