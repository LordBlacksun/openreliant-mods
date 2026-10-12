// Saturn's ring (Realistic Planets). The texture's alpha is the share of the light the ring stops seen
// face on, 1 - exp(-tau), and its colour the reflectance of the ring's particles, S. As a layer that
// scatters the light once, with mu and mu0 the cosines of the view's and the sun's angles from the
// ring's pole, the ring lets through exp(-tau / mu) of the light behind it, and toward the eye it
// scatters S mu0 / (mu + mu0) (1 - exp(-tau (1/mu + 1/mu0))) of the sunlight on the side the sun
// lights, and S mu0 / (mu - mu0) (exp(-tau / mu) - exp(-tau / mu0)) on the other side, the light that
// comes through. Where Saturn stands between the ring and the sun, the ring gets no sunlight.
//
// The frame blends colours as they're encoded, not in linear light, so the colour and the alpha are
// chosen to give the right result over a black sky exactly, and over a planet behind the ring at the
// brightness `parameters.z`, encoded.
//
// parameters.x: unused.
// parameters.y: the smallest cosine of the view angle, so that the ring stays finite edge on.
// parameters.z: the brightness behind the ring that the blend is fitted to, encoded.

// Saturn's equatorial and polar radius in the model's units, as `sphere.py` makes its detailed
// model.
const float ringsSaturnRadius = 2044626.0;
const float ringsSaturnPolar = 1844330.0;

// Whether Saturn stands between a point of its frame, `local`, and the sun along `sun`: whether the
// ray toward the sun meets the flattened ball.
bool ringsInSaturnShadow(vec3 local, vec3 sun) {
    vec3 scale = vec3(1.0 / ringsSaturnRadius, 1.0 / ringsSaturnPolar, 1.0 / ringsSaturnRadius);
    vec3 p = local * scale;
    vec3 d = sun * scale;
    float a = dot(d, d);
    float b = dot(p, d);
    float c = dot(p, p) - 1.0;
    return b < 0.0 && b * b - a * c > 0.0;
}

void surface(inout Surface s, vec4 parameters, float time) {
    vec3 sun = objectDirection(s.toSun);
    vec3 eye = objectDirection(s.toEye);
    float mu = max(abs(eye.y), parameters.y);
    float mu0 = abs(sun.y);
    float clear = 1.0 - s.alpha;
    float tau = -log(max(clear, 1e-6));
    float through = exp(-tau / mu);
    vec3 albedo = decoded(s.color);
    vec3 scattered = vec3(0.0);
    if (mu0 > 1e-4 && !ringsInSaturnShadow(s.local, sun)) {
        if (sun.y * eye.y > 0.0) {
            scattered = albedo * mu0 / (mu + mu0) * (1.0 - exp(-tau * (1.0 / mu + 1.0 / mu0)));
        } else if (abs(mu - mu0) > 1e-3) {
            scattered = albedo * mu0 / (mu - mu0) * (exp(-tau / mu) - exp(-tau / mu0));
        } else {
            scattered = albedo * tau / mu * exp(-tau / mu);
        }
    }
    vec3 overSky = encoded(scattered);
    vec3 behind = vec3(parameters.z);
    vec3 overPlanet = encoded(scattered + through * decoded(behind));
    // What's behind shows through by 1 - alpha: exact over the planet's brightness, for the luminance.
    float kept = clamp(luminance(overPlanet - overSky) / parameters.z, 0.0, 1.0);
    s.alpha = 1.0 - kept;
    s.glow = s.alpha > 1e-4 ? min(overSky / s.alpha, vec3(1.0)) : vec3(0.0);
    s.color = vec3(0.0);
}
