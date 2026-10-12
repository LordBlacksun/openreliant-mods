// Earth (Realistic Planets, planets.luau): lit by Minnaert's law (limb.glsl), as the other planets
// are, with its city lights, its texture's emissive map from NASA's Black Marble, on its night
// side alone. The lights fade in as the sun sets, and show whole once it is 6 degrees below the
// horizon, the end of civil twilight. The Black Marble is a picture of clear nights, so where the
// texture shows thick clouds, which are bright, the lights are dimmed, as the clouds would hide them.
//
// parameters.xyz: k for red, green and blue.
// parameters.w: the least cosine of the view the law was fitted at.

// The cosine of the sun's angle from overhead at which the lights show whole: 96 degrees.
const float earthNight = -0.1045;
// The luminance of the texture in linear light at which clouds start to dim the lights, at which
// they dim them the most, and the share of the lights that thick clouds hide.
const float earthCloudFrom = 0.4;
const float earthCloudTo = 0.8;
const float earthCloudHides = 0.85;

#include "limb.glsl"

void surface(inout Surface s, vec4 parameters, float time) {
    vec3 linear = decoded(s.color);
    float cosine = dot(s.normal, s.toSun);
    if (!realisticPlanetsLimb(s, parameters)) return;
    float clouds = smoothstep(earthCloudFrom, earthCloudTo, luminance(linear));
    s.glow *= (1.0 - smoothstep(earthNight, 0.0, cosine)) * (1.0 - earthCloudHides * clouds);
}
