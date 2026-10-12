// Realistic Planets (planets.luau): a body's haze, by single scattering of sunlight, which a body's
// function includes with its own numbers (`RealisticPlanetsHaze`), as neptune.glsl and titan.glsl
// do. The function draws two things. On the body's texture, where parameters.w is the least cosine
// of the view for Minnaert's law, it lights the disk by that law (limb.glsl) and adds the haze in
// front of it. On the ring that OpenReliant draws behind the body for its atmosphere
// (records.luau), where the parameters are 0, it draws the haze beyond the disk. The texture's
// points are in its model's units, and the ring's in the body's radii. The mod's sources work the
// model out in the same way, in sources/realistic-planets/scattering.py, to fit each body's
// numbers, and the mod's README describes it.
//
// Each pixel's line of sight is followed through the haze in steps. Each step scatters the sunlight
// that reaches it toward the eye, as much as its haze's extinction, single-scattering albedo and
// phase function say, and the haze between it and the eye dims that light. The sunlight that
// reaches a step is dimmed by the main haze on its way, Chapman's integral, so the haze on the
// night side is lit only high up, where the sun still reaches it past the body's edge. Beyond the
// disk the line is followed through. Over the disk it is followed down to the disk, and only the
// light the texture doesn't hold already counts: the texture is the body as seen from the front, so
// over the disk the haze adds what its phase function gives beyond what it gives there, which with
// the sun behind the body is the crescent its forward scattering lights. Everything is worked out
// in the three filters of the body's fit, in the order of their wavelengths, and turned into the
// game's colours at the end, on the same scale as the texture. The haze is added in linear light,
// lit by the sun as the disk is (`scattered`), so the disk and the ring meet at the edge.

#include "limb.glsl"

// A body's haze, in its fit's three filters, in the order of their wavelengths.
struct RealisticPlanetsHaze {
    // The sphere's radius in the game, km: where the texture's disk ends.
    float unit;
    // The radius the main haze's extinction is given at, and the radius it is cut off at, km.
    float reference;
    float top;
    // The main haze's extinction at `reference`, per km, and its scale height, km.
    vec3 extinction;
    vec3 scale;
    // A detached layer: its extinction at its peak, per km, and the peak's radius and width, km. A
    // body without one has an extinction of 0.
    vec3 layer;
    vec3 layerRadius;
    vec3 layerWidth;
    // The cosine of the scattering angle at the phase angle the texture shows the body at.
    float textureCosine;
    // The haze's single-scattering albedo, and its phase function: two Henyey-Greenstein lobes,
    // their asymmetries and their shares of the light, and Rayleigh's, the gas's, with the rest.
    vec3 albedo;
    vec3 firstLobe;
    vec3 secondLobe;
    vec3 firstShare;
    vec3 secondShare;
    // The haze's I/F in the three filters to the game's linear sRGB, as the texture takes the
    // body's brightness in them (columns), its blue divided by the key light's as the texture's is.
    mat3 color;
    // How much of the haze's light blooms.
    float bloom;
};

// The steps along a line of sight, spaced most closely where it passes nearest the body, or where
// it meets the disk.
const int realisticPlanetsHazeSteps = 32;
const float realisticPlanetsHazeSpread = 3.0;
// A pixel that spans more than half the thinnest scale height takes up to this many lines of sight
// across it, so that the haze doesn't shimmer as the body grows small.
const int realisticPlanetsHazeMostSamples = 4;

// exp(y^2) erfc(y) for y >= 0, within 0.02% (a rational fit).
vec3 realisticPlanetsHazeErfcx(vec3 y) {
    return (1.0 + y * (0.88584516 + y * 0.31615637)) / (1.0 + y * (2.01758094 + y * (1.57175152 + y * 0.56037257)));
}

// The main haze's extinction at radius r, km, held below exp(80) deep down, where it would
// overflow.
vec3 realisticPlanetsHazeMain(RealisticPlanetsHaze haze, float r) {
    return haze.extinction * exp(min(-(r - haze.reference) / haze.scale, vec3(80.0)));
}

// The main haze's optical depth from radius r toward a direction cosChi from the vertical, out of
// the haze: Chapman's integral, the extinction at r times its scale height H times sqrt(pi x / 2)
// exp(y^2) erfc(y), with x = r / H and y = sqrt(x / 2) cosChi. Below the horizon, the line passes
// its lowest point first, and the depth is twice that from there less that back from r.
vec3 realisticPlanetsHazeTowardSun(RealisticPlanetsHaze haze, float r, float cosChi) {
    vec3 here = realisticPlanetsHazeMain(haze, r) * haze.scale * sqrt(1.5707963 * r / haze.scale) * realisticPlanetsHazeErfcx(sqrt(0.5 * r / haze.scale) * abs(cosChi));
    if (cosChi >= 0.0) return here;
    float lowest = r * sqrt(max(1.0 - cosChi * cosChi, 0.0));
    return 2.0 * realisticPlanetsHazeMain(haze, lowest) * haze.scale * sqrt(1.5707963 * lowest / haze.scale) - here;
}

// Henyey and Greenstein's phase function of asymmetry g, at the cosine of the scattering angle.
vec3 realisticPlanetsHazeLobe(vec3 g, float cosTheta) {
    return (1.0 - g * g) / pow(1.0 + g * g - 2.0 * g * cosTheta, vec3(1.5));
}

// The haze's phase function, its lobes and Rayleigh's together, at the cosine of the scattering
// angle.
vec3 realisticPlanetsHazePhase(RealisticPlanetsHaze haze, float cosTheta) {
    vec3 rayleigh = 1.0 - haze.firstShare - haze.secondShare;
    return haze.firstShare * realisticPlanetsHazeLobe(haze.firstLobe, cosTheta) + haze.secondShare * realisticPlanetsHazeLobe(haze.secondLobe, cosTheta)
        + rayleigh * 0.75 * (1.0 + cosTheta * cosTheta);
}

// The haze's I/F in each filter along the line of sight along `ray` that passes `through` km from
// the body's middle, nearest it toward `outward`, with the sun toward `sun`: through the haze where
// the line passes beyond the disk, and in front of it where the line meets it.
vec3 realisticPlanetsHazeLine(RealisticPlanetsHaze haze, float through, vec3 outward, vec3 ray, vec3 sun) {
    if (through >= haze.top) return vec3(0.0);
    bool meets = through < haze.unit;
    vec3 phase = realisticPlanetsHazePhase(haze, dot(sun, ray));
    if (meets) phase = max(phase - realisticPlanetsHazePhase(haze, haze.textureCosine), vec3(0.0));
    if (all(lessThanEqual(phase, vec3(0.0)))) return vec3(0.0);
    vec3 middle = outward * through;
    float chord = sqrt(haze.top * haze.top - through * through);
    float hit = meets ? sqrt(haze.unit * haze.unit - through * through) : 0.0;
    float spacing = 1.0 / sinh(realisticPlanetsHazeSpread);
    vec3 depth = vec3(0.0);
    vec3 light = vec3(0.0);
    for (int i = 0; i < realisticPlanetsHazeSteps; i++) {
        float u = (float(i) + 0.5) / float(realisticPlanetsHazeSteps);
        float along;
        float stride;
        if (meets) {
            // From the top of the haze on the eye's side down to the disk, the steps closer as the
            // square of their place, nearest the disk.
            float t = 1.0 - u;
            along = -hit - (chord - hit) * t * t;
            stride = (chord - hit) * 2.0 * t / float(realisticPlanetsHazeSteps);
        } else {
            float v = u * 2.0 - 1.0;
            along = chord * sinh(realisticPlanetsHazeSpread * v) * spacing;
            stride = chord * realisticPlanetsHazeSpread * cosh(realisticPlanetsHazeSpread * v) * spacing * 2.0 / float(realisticPlanetsHazeSteps);
        }
        vec3 p = middle + ray * along;
        float r = length(p);
        vec3 fromPeak = (vec3(r) - haze.layerRadius) / haze.layerWidth;
        vec3 extinction = realisticPlanetsHazeMain(haze, r) + haze.layer * exp(-0.5 * fromPeak * fromPeak);
        vec3 piece = extinction * stride;
        light += piece * exp(-realisticPlanetsHazeTowardSun(haze, r, dot(p, sun) / r) - depth - 0.5 * piece);
        depth += piece;
    }
    return haze.albedo * phase * light / 4.0;
}

// The body's function: its disk lit by Minnaert's law with its haze in front, where `parameters`
// are the law's, or its haze beyond the disk on its ring, where they are 0.
void realisticPlanetsHaze(inout Surface s, vec4 parameters, RealisticPlanetsHaze haze) {
    bool disk = parameters.w > 0.0;
    // The eye, the line of sight through the pixel and the sun, in the body's frame, in km. On the
    // texture, the pixel lies on the sphere, whose radius in the model's units its distance from
    // the middle gives.
    float km = disk ? haze.unit / length(s.local) : haze.unit;
    vec3 eye = objectPoint(vec3(0.0)) * km;
    vec3 ray = normalize(s.local * km - eye);
    vec3 sun = objectDirection(s.toSun);
    vec3 nearest = eye - dot(eye, ray) * ray;
    float through = length(nearest);
    // How far the lines of sight through the pixel spread from the body's middle, km.
    float spread = max(fwidth(through), 1e-3);
    vec3 light = vec3(0.0);
    if (dot(sun, sun) > 0.5 && through > 1e-3) {
        float thinnest = min(min(haze.scale.x, haze.scale.y), haze.scale.z);
        int samples = int(clamp(ceil(2.0 * spread / thinnest), 1.0, float(realisticPlanetsHazeMostSamples)));
        vec3 outward = nearest / through;
        for (int k = 0; k < samples; k++) {
            float line = max(through + ((float(k) + 0.5) / float(samples) - 0.5) * spread, 0.0);
            // The disk takes the lines that meet it, and the ring those that pass beyond it, as
            // the planet hides the ring within its edge: each gives its side of the edge's pixels,
            // which show the planet and the sky round it, as the function runs once for each.
            light += realisticPlanetsHazeLine(haze, disk ? min(line, haze.unit - 1e-3) : max(line, haze.unit), outward, ray, sun);
        }
        light = max(haze.color * (light / float(samples)), vec3(0.0));
    }
    if (!disk) {
        s.color = vec3(0.0);
        s.sunlight = vec3(0.0);
        s.scattered = light;
        s.bloom *= haze.bloom;
        return;
    }
    if (!realisticPlanetsLimb(s, parameters)) return;
    s.scattered = light;
    // The haze's part of the pixel's light blooms as the ring's does: its share of the encoded
    // light that the bloom takes, with the disk lit as a white sun would light it.
    vec3 lit = decoded(s.color) * s.sunlight;
    float whole = luminance(encoded(lit + light));
    float share = whole > 0.0 ? 1.0 - luminance(encoded(lit)) / whole : 0.0;
    s.bloom *= 1.0 - (1.0 - haze.bloom) * share;
}
