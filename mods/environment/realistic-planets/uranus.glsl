// Realistic Planets (planets.luau): Uranus and its haze (haze.glsl): a thin haze above the clouds
// like Neptune's, but about twice as thick, since Uranus is hazier, and with a larger scale height,
// about 22 km, to match its colder atmosphere. The mod's README gives the sources of the numbers.

#include "haze.glsl"

const RealisticPlanetsHaze uranusHaze = RealisticPlanetsHaze(
    // Uranus's equatorial radius at 1 bar, km, and its polar radius's share of it.
    25559.0, 0.9771, 25559.0,
    // The haze's optical depth and scale height, the same in blue, green and red.
    vec3(0.0046),
    vec3(22.0),
    // No detached layer.
    vec3(0.0), 0.0, 1.0,
    // Its albedo, and one forward lobe like Neptune's.
    vec3(1.0),
    vec3(0.59), vec3(0.0), vec3(1.0), vec3(0.0),
    // The cloud tops' forward light, its strength and lobe: about twice the crescent's light at 147
    // degrees, as Voyager 2's frames show it, with Neptune's lobe.
    0.34, 0.8,
    // The texture shows Uranus as seen from the sun; blue, green and red to the texture's channels,
    // at the texture's brightness, and the share of the haze's light that blooms.
    0.0,
    mat3(0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0),
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, uranusHaze);
}
