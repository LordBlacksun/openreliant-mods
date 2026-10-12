// Earth (Realistic Planets, planets.luau): lit by Minnaert's law (limb.glsl), as the other planets
// are, with the blue of its air along the limb (haze.glsl), and its city lights, its texture's
// emissive map from NASA's Black Marble, on its night side alone. The lights fade in as the sun sets, and show whole once it is 6 degrees below the
// horizon, the end of civil twilight. The Black Marble is a picture of clear nights, so where the
// texture shows thick clouds, which are bright, the lights are dimmed, as the clouds would hide them.
//
// parameters.xyz: k for red, green and blue, on the planet's texture; 0 on its air's ring.
// parameters.w: the least cosine of the view the law was fitted at; 0 on its air's ring.

// The cosine of the sun's angle from overhead at which the lights show whole: 96 degrees.
const float earthNight = -0.1045;
// The luminance of the texture in linear light at which clouds start to dim the lights, at which
// they dim them the most, and the share of the lights that thick clouds hide.
const float earthCloudFrom = 0.4;
const float earthCloudTo = 0.8;
const float earthCloudHides = 0.85;

#include "haze.glsl"

// The air: Rayleigh's scattering by its molecules alone, about 8 km a scale height. The haze of its
// dust and droplets, low down, is in the texture.
const RealisticPlanetsHaze earthHaze = RealisticPlanetsHaze(
    // Earth's equatorial radius, km. Earth is round.
    6378.0, 1.0, 6378.0,
    // The air's optical depth down to sea level, at the blue, green and red channels' wavelengths,
    // and its scale height.
    vec3(0.219, 0.107, 0.069),
    vec3(8.0),
    // No detached layer.
    vec3(0.0), 0.0, 1.0,
    // Its albedo, and Rayleigh's phase function alone.
    vec3(1.0),
    vec3(0.0), vec3(0.0), vec3(0.0), vec3(0.0),
    // The phase angle the texture's haze is taken at; blue, green and red to the texture's channels,
    // at the texture's brightness, half Earth's true one; and a quarter of the air's light blooming.
    19.0,
    mat3(0.0, 0.0, 0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.0),
    0.25);

void surface(inout Surface s, vec4 parameters, float time) {
    vec3 linear = decoded(s.color);
    float cosine = dot(s.normal, s.toSun);
    realisticPlanetsHaze(s, parameters, earthHaze);
    if (parameters.w <= 0.0 || dot(s.normal, s.normal) < 0.5) return;
    float clouds = smoothstep(earthCloudFrom, earthCloudTo, luminance(linear));
    s.glow *= (1.0 - smoothstep(earthNight, 0.0, cosine)) * (1.0 - earthCloudHides * clouds);
}
