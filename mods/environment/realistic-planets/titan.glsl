// Realistic Planets (planets.luau): Titan and its haze (haze.glsl), as Cassini's frames of 2009 and
// 2010 show it from 28 to 164 degrees of phase: a thick orange haze, its extinction rising steeply
// toward the blue, about 28 km a scale height, with a detached layer about 450 km above the ground.
// The mod's README gives the sources of the numbers.

#include "haze.glsl"

const RealisticPlanetsHaze titanHaze = RealisticPlanetsHaze(
    // The haze's edge in green, km, where the texture's disk ends. Titan is round.
    2741.0, 1.0, 2741.0,
    // The main haze's optical depth and scale heights, in Cassini's blue, green and red filters.
    vec3(2.55, 0.723, 0.369),
    vec3(24.2, 27.5, 30.1),
    // The detached layer: its peak's extinction, per km, its height and its width, km.
    vec3(2.25e-05, 1.11e-05, 7.7e-06), 288.0, 50.0,
    // Its albedo, and two forward lobes, the second in blue alone.
    vec3(1.0, 0.854, 0.923),
    vec3(0.758, 0.682, 0.689), vec3(0.232, 0.594, 0.594), vec3(0.556, 1.0, 1.0), vec3(0.444, 0.0, 0.0),
    // The cloud tops' forward light, its strength and lobe: about 1.3 times the crescent's light at
    // 141 degrees, as Cassini's frames show it.
    0.6, 0.8,
    // The mean phase angle of the texture's frames, the filters to the texture's colours, and the
    // share of the haze's light that blooms: a quarter, since more bloom would spread the bright
    // haze of a backlit Titan well past what Cassini saw.
    35.0,
    mat3(-0.14988, 0.21081, 0.55748, 0.27673, 0.35667, -0.02695, 0.35095, -0.00266, -0.00667),
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, titanHaze);
}
