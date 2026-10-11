// Realistic Planets (planets.luau): a planet's limb as its photometry was measured, by Minnaert's
// law, I/F = B mu0^k mu^(k-1), with an exponent k for each colour channel. OpenReliant already lights
// a planet by the sun's cosine mu0, softened past the terminator, which falls off much as mu0^k does,
// so this adds the part that depends on the view: mu^(k-1), in linear light. With k below 1, as on
// Neptune, it brightens the lit limb and makes it paler, as the planet's haze does. A surface
// function can't read where the light comes from yet, so mu0^k itself isn't applied
// (OpenReliant/openreliant#1084).
//
// parameters.xyz: k for red, green and blue.
// parameters.w: the least cosine of the view the law was fitted at. Nearer the limb the law isn't
// known, and the factor stays as it is there.

// A colour in linear light encoded in sRGB, as `encoded` does, but not clipped at 1, so that a bright
// texel the factor lifts past 1 keeps its colour until the planet is lit, which dims it again.
vec3 realisticPlanetsEncoded(vec3 c) {
    c = max(c, 0.0);
    return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, greaterThan(c, vec3(0.0031308)));
}

void surface(inout Surface s, vec4 parameters, float time) {
    // Sprites and effects have no normal, and are left as they are.
    if (dot(s.normal, s.normal) < 0.5) return;
    float mu = max(dot(s.normal, s.toEye), parameters.w);
    s.color = realisticPlanetsEncoded(decoded(s.color) * pow(vec3(mu), parameters.xyz - 1.0));
}
