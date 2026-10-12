// Realistic Planets: a planet lit as its photometry was measured, by Minnaert's law,
// I/F = B mu0^k mu^(k-1), with an exponent k for each colour channel, where mu0 and mu are the
// cosines of the sun's and the view's angles from the surface's normal, and the texture holds B. The
// sun's part, mu0^k, sets how much of the sun lights the pixel; the view's part, mu^(k-1), goes into
// the colour, in linear light. With k below 1, as on Neptune, it brightens the lit limb and makes it
// paler, as the planet's haze does. The bodies' functions include it (planets.luau).
//
// parameters.xyz: k for red, green and blue.
// parameters.w: the smallest cosine of the view angle that the law was fitted to. Closer to the
// limb the law isn't known, and the view's factor keeps the value it has there.

// Lights the pixel `s` by Minnaert's law, with the exponents and the smallest cosine in
// `parameters`: the view's part goes into its colour, and the sun's part sets how much of the sun
// lights it. Returns false for sprites and effects, which have no normal, and leaves them as they
// are.
bool realisticPlanetsLimb(inout Surface s, vec4 parameters) {
    if (dot(s.normal, s.normal) < 0.5) return false;
    float mu = max(dot(s.normal, s.toEye), parameters.w);
    float mu0 = max(dot(s.normal, s.toSun), 0.0);
    // Encoded again without clipping at 1, so that a bright texel the view's factor lifts past 1
    // keeps its colour until the planet is lit, which dims it again.
    s.color = encodedPastWhite(decoded(s.color) * pow(vec3(mu), parameters.xyz - 1.0));
    s.sunlight = pow(vec3(mu0), parameters.xyz);
    return true;
}
