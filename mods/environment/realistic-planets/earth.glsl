// Earth (Realistic Planets, planets.luau): lit by Minnaert's law, as `minnaert.glsl` lights the other
// planets, with its city lights, its texture's emissive map from NASA's Black Marble, on its night
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

// A colour in linear light encoded in sRGB, not clipped at 1, as `minnaert.glsl` has it.
vec3 earthEncoded(vec3 c) {
    c = max(c, 0.0);
    return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, greaterThan(c, vec3(0.0031308)));
}

void surface(inout Surface s, vec4 parameters, float time) {
    if (dot(s.normal, s.normal) < 0.5) return;
    vec3 linear = decoded(s.color);
    float mu = max(dot(s.normal, s.toEye), parameters.w);
    float cosine = dot(s.normal, s.toSun);
    s.color = earthEncoded(linear * pow(vec3(mu), parameters.xyz - 1.0));
    s.sunlight = pow(vec3(max(cosine, 0.0)), parameters.xyz);
    float clouds = smoothstep(earthCloudFrom, earthCloudTo, dot(linear, vec3(0.2126, 0.7152, 0.0722)));
    s.glow *= (1.0 - smoothstep(earthNight, 0.0, cosine)) * (1.0 - earthCloudHides * clouds);
}
