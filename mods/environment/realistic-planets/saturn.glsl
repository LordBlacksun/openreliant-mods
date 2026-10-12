// Saturn (Realistic Planets, planets.luau): lit by Minnaert's law (limb.glsl) like the other
// planets, with its haze (haze.glsl) as Cassini's frames show it at 151 to 176 degrees of phase,
// and shaded by its ring. The haze is yellow, absorbing in the blue, about 30 to 40 km a scale height,
// mostly Rayleigh's scattering with a narrow forward lobe. The mod's README gives the numbers' sources.
//
// The ring's shadow: in Saturn's frame the ring lies in the plane of the equator, and the ray from
// each pixel toward the sun crosses that plane at some radius. Where the ring is at that radius, it
// lets through exp(-tau / mu0) of the sunlight, where tau is its optical depth seen face on and mu0
// the cosine of the sun's angle from the ring's pole. It dims both the disk's sunlight and the
// haze's light.
//
// parameters.xyz: k for red, green and blue, on the planet's texture; 0 on its haze's ring.
// parameters.w: the smallest cosine of the view angle that the law was fitted to; 0 on its haze's
// ring.

#include "haze.glsl"

const RealisticPlanetsHaze saturnHaze = RealisticPlanetsHaze(
    // Saturn's equatorial radius at 1 bar, km, its polar radius's share of it, and the unit of the
    // ring the haze beyond the disk is drawn on: the rings' outer edge, which OpenReliant takes as
    // the planet's radius.
    60268.0, 0.902, 141000.0,
    // The haze's optical depth and scale heights, in Cassini's blue, green and red filters.
    vec3(0.055, 0.050, 0.064),
    vec3(40.4, 29.0, 30.4),
    // No detached layer.
    vec3(0.0), 0.0, 1.0,
    // Its albedo, and a narrow forward lobe with a ninth of the light, Rayleigh's with the rest.
    vec3(0.38, 1.0, 0.91),
    vec3(0.964), vec3(0.0), vec3(0.112), vec3(0.0),
    // The cloud tops' forward light, its strength and lobe: four to eight times the crescent's light
    // at 151 degrees, cream rather than grey, as Cassini's frames show it.
    0.83, 0.8,
    // The texture shows Saturn as seen from the sun; the filters to the texture's colours, and the
    // share of the haze's light that blooms.
    0.0,
    mat3(-0.10745, 0.14639, 0.44356, 0.22973, 0.33104, -0.02183, 0.31752, -0.00177, -0.00611),
    0.25);

// The ring's inner and outer radius in the model's units, as `sphere.py` makes it, and its optical
// depth seen face on in bins evenly spaced between them, each the mean of the light the texture's
// texels in it let through (`saturn/ringdepth.py`).
const float saturnRingInner = 2510492.0;
const float saturnRingOuter = 4783505.0;
const int saturnRingBins = 128;
const float saturnRingTau[saturnRingBins] = float[](
    0.006, 0.036, 0.03, 0.047, 0.076, 0.063, 0.071, 0.066, 0.066, 0.079, 0.088, 0.092, 0.1, 0.097, 0.108, 0.119,
    0.115, 0.118, 0.091, 0.102, 0.213, 0.084, 0.131, 0.186, 0.075, 0.121, 0.051, 0.15, 0.07, 0.087, 0.191, 0.167,
    0.102, 0.152, 0.652, 1.438, 1.06, 0.908, 0.913, 0.722, 0.756, 0.897, 0.834, 0.925, 0.775, 0.822, 0.875, 1.21,
    1.535, 1.658, 2.723, 2.133, 1.457, 1.852, 1.33, 1.47, 1.512, 2.03, 2.303, 2.372, 2.426, 2.265, 2.299, 2.376,
    2.319, 2.188, 2.13, 2.094, 2.063, 1.793, 1.819, 1.795, 1.521, 1.617, 1.541, 1.424, 1.467, 1.475, 1.675, 2.132,
    2.037, 1.609, 0.789, 0.131, 0.099, 0.068, 0.071, 0.043, 0.13, 0.225, 0.132, 0.222, 0.815, 0.853, 0.875, 0.724,
    0.63, 0.531, 0.531, 0.506, 0.482, 0.471, 0.457, 0.437, 0.434, 0.425, 0.42, 0.43, 0.488, 0.422, 0.496, 0.488,
    0.432, 0.229, 0.419, 0.58, 0.492, 0.513, 0.514, 0.482, 0.009, 0.005, 0.004, 0.004, 0.003, 0.004, 0.009, 0.002);

// The share of the sun the ring lets through to a point of Saturn's frame, `local`, the sun along
// `sun` in that frame.
float saturnRingShade(vec3 local, vec3 sun) {
    if (abs(sun.y) < 1e-4) return 1.0;
    float t = -local.y / sun.y;
    if (t <= 0.0) return 1.0;
    float radius = length((local + t * sun).xz);
    if (radius <= saturnRingInner || radius >= saturnRingOuter) return 1.0;
    float at = (radius - saturnRingInner) / (saturnRingOuter - saturnRingInner) * float(saturnRingBins) - 0.5;
    int below = clamp(int(floor(at)), 0, saturnRingBins - 1);
    int above = min(below + 1, saturnRingBins - 1);
    float tau = mix(saturnRingTau[below], saturnRingTau[above], clamp(at - float(below), 0.0, 1.0));
    return exp(-tau / abs(sun.y));
}

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsHaze(s, parameters, saturnHaze);
    // On the texture the pixel lies on the disk, in the model's units. On the haze's ring, whose
    // unit is the rings' outer edge, the line of sight crosses the plane that faces the camera
    // through the middle about where it passes nearest Saturn.
    float shade = saturnRingShade(parameters.w > 0.0 ? s.local : s.local * saturnRingOuter, objectDirection(s.toSun));
    s.sunlight *= shade;
    s.scattered *= shade;
}
