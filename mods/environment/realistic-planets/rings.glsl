// Saturn's ring (Realistic Planets). The texture's alpha is the share of the light the ring stops seen
// face on, and its colour the reflectance of the ring's particles. Seen from any angle, the ring lets
// through exp(-tau / mu) of the light behind it, and scatters
// S mu0 / (mu + mu0) (1 - exp(-tau (1/mu + 1/mu0))) of the sunlight toward the eye, as a layer that
// scatters the light once, where mu and mu0 are the cosines of the view's and the sun's angles from the
// ring's pole. A surface function can't read where the light comes from, so the ring is lit as if the
// sun stood at a set height, from either side, as the original's ring is.
//
// The frame blends colours as they're encoded, not in linear light, so the colour and the alpha are
// chosen to give the right result over a black sky exactly, and over a planet behind the ring at the
// brightness `parameters.z`, encoded.
//
// parameters.x: the cosine of the sun's angle from the ring's pole that the ring is lit for.
// parameters.y: the least cosine of the view's angle, so that the ring seen edge on stays finite.
// parameters.z: the brightness behind the ring that the blend is fitted to, encoded.
void surface(inout Surface s, vec4 parameters, float time) {
    float mu = dot(s.normal, s.normal) > 0.5 ? abs(dot(s.normal, s.toEye)) : 0.5;
    mu = max(mu, parameters.y);
    float mu0 = parameters.x;
    float clear = 1.0 - s.alpha;
    float through = pow(clear, 1.0 / mu);
    vec3 scattered = decoded(s.color) * mu0 / (mu + mu0) * (1.0 - pow(clear, 1.0 / mu + 1.0 / mu0));
    vec3 overSky = encoded(scattered);
    vec3 behind = vec3(parameters.z);
    vec3 overPlanet = encoded(scattered + through * decoded(behind));
    // What's behind shows through by 1 - alpha: exact over the planet's brightness, for the luminance.
    float kept = clamp(dot(overPlanet - overSky, vec3(0.2126, 0.7152, 0.0722)) / parameters.z, 0.0, 1.0);
    s.alpha = 1.0 - kept;
    s.glow = s.alpha > 1e-4 ? min(overSky / s.alpha, vec3(1.0)) : vec3(0.0);
    s.color = vec3(0.0);
}
