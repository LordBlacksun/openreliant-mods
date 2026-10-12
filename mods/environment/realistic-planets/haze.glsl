// Realistic Planets (planets.luau): a body's atmospheric haze, the sunlight it scatters toward the
// eye. Each body's shader, such as titan.glsl, includes it with its own numbers
// (`RealisticPlanetsHaze`), which describe its kind of atmosphere: how much haze it has and how high
// it reaches, its colour, and how strongly it scatters light forward. The mod's README gives each
// body's numbers and where they come from.
//
// The function draws two things. On the body's texture, where parameters.w is the least cosine of
// the view for Minnaert's law, it lights the disk by that law (limb.glsl) and adds the haze in front
// of it. On the ring that OpenReliant draws behind the body for its atmosphere (records.luau), where
// the parameters are 0, it draws the haze beyond the disk. The texture's points are in its model's
// units, and the ring's in its own unit (`ringUnit`). A flattened body is worked out in a frame
// stretched along its pole, the model's Y axis, where it is round.
//
// The haze's extinction falls exponentially with height above the body's sphere, with a detached
// layer above it where the body has one. Each pixel's line of sight is followed through the haze in
// steps, and each step scatters the sunlight that reaches it toward the eye, once, as much as the
// haze's extinction, single-scattering albedo and phase function say, dimmed by the haze between it
// and the eye. The sunlight is dimmed on its way in too, by Chapman's integral, so the haze on the
// night side is lit only high up, where the sun still reaches it past the body's edge. Over the disk
// the line ends at the disk, and only the light the texture doesn't hold already counts: the texture
// shows the body, haze included, at one phase angle, so the haze over the disk adds what its phase
// function gives beyond what it gives there, which with the sun behind the body is the crescent its
// forward scattering lights. Everything is worked out in the haze's three bands, a camera's filters
// or three wavelengths, turned into the game's colours at the end, and added in linear light, lit by
// the sun as the disk is (`scattered`), so the disk and the ring meet at the edge.

#include "limb.glsl"

// A body's haze, each vec3 in its three bands, from blue to red.
struct RealisticPlanetsHaze {
    // The sphere's radius in the game, km: where the texture's disk ends. A flattened body's polar
    // radius as a share of it, along the model's Y axis: 1 for a round one. The unit of the ring the
    // haze beyond the disk is drawn on, km: the radius OpenReliant takes for the body, half the widest
    // span of its model, which is `unit` unless the model holds more, such as Saturn's rings.
    float unit;
    float polar;
    float ringUnit;
    // How much haze there is: its optical depth straight down to the sphere, and its scale height,
    // km, the height over which its extinction falls by e.
    vec3 depth;
    vec3 scale;
    // A detached layer: its extinction at its peak, per km, and the peak's height above the sphere
    // and its width, km. A body without one has an extinction of 0.
    vec3 layer;
    float layerHeight;
    float layerWidth;
    // The haze's colour: its single-scattering albedo, the share of the light it meets that it
    // scatters rather than absorbs.
    vec3 albedo;
    // How it scatters the light: two Henyey-Greenstein lobes, their asymmetries, from -1 backward to
    // 1 forward, and their shares of the light, and Rayleigh's phase function, the gas's, with the
    // rest.
    vec3 firstLobe;
    vec3 secondLobe;
    vec3 firstShare;
    vec3 secondShare;
    // The phase angle the texture shows the body at, degrees.
    float texturePhase;
    // The haze's I/F in its three bands to the game's linear sRGB (columns), as the body's texture
    // takes its colours and brightness, and how much of the haze's light blooms.
    mat3 color;
    float bloom;
};

// The steps along a line of sight, spaced most closely where it passes nearest the body, or where
// it meets the disk.
const int realisticPlanetsHazeSteps = 32;
const float realisticPlanetsHazeSpread = 3.0;
// A pixel that spans more than half the thinnest scale height takes up to this many lines of sight
// across it, so that the haze doesn't shimmer as the body grows small.
const int realisticPlanetsHazeMostSamples = 4;
// The haze is cut off this many scale heights above the sphere, where its extinction is a
// two-hundred-millionth of the sphere's, and a detached layer this many widths above its peak.
const float realisticPlanetsHazeScales = 20.0;
const float realisticPlanetsHazeWidths = 5.0;

// exp(y^2) erfc(y) for y >= 0, within 0.02% (a rational fit).
vec3 realisticPlanetsHazeErfcx(vec3 y) {
    return (1.0 + y * (0.88584516 + y * 0.31615637)) / (1.0 + y * (2.01758094 + y * (1.57175152 + y * 0.56037257)));
}

// The haze's height cut off at, km above the sphere.
float realisticPlanetsHazeTop(RealisticPlanetsHaze haze) {
    float top = realisticPlanetsHazeScales * max(max(haze.scale.x, haze.scale.y), haze.scale.z);
    return any(greaterThan(haze.layer, vec3(0.0))) ? max(top, haze.layerHeight + realisticPlanetsHazeWidths * haze.layerWidth) : top;
}

// The main haze's extinction at radius r, km, held below exp(80) deep down, where it would
// overflow.
vec3 realisticPlanetsHazeMain(RealisticPlanetsHaze haze, float r) {
    return haze.depth / haze.scale * exp(min(-(r - haze.unit) / haze.scale, vec3(80.0)));
}

// The main haze's optical depth from radius r toward a direction cosChi from the vertical, out of
// the haze: Chapman's integral, the extinction at r times its scale height H times
// sqrt(pi x / 2) exp(y^2) erfc(y), with x = r / H and y = sqrt(x / 2) cosChi. Below the horizon, the
// line passes its lowest point first, and the depth is twice that from there less that back from r.
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

// The haze's I/F along the line of sight along `ray` that passes `through` km from the body's
// middle, nearest it toward `outward`, with the sun toward `sun`: through the haze where the line
// passes beyond the disk, and in front of it where the line meets it.
vec3 realisticPlanetsHazeLine(RealisticPlanetsHaze haze, float through, vec3 outward, vec3 ray, vec3 sun) {
    float top = haze.unit + realisticPlanetsHazeTop(haze);
    if (through >= top) return vec3(0.0);
    bool meets = through < haze.unit;
    vec3 phase = realisticPlanetsHazePhase(haze, dot(sun, ray));
    if (meets) phase = max(phase - realisticPlanetsHazePhase(haze, -cos(radians(haze.texturePhase))), vec3(0.0));
    if (all(lessThanEqual(phase, vec3(0.0)))) return vec3(0.0);
    vec3 middle = outward * through;
    float chord = sqrt(top * top - through * through);
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
        float fromPeak = (r - haze.unit - haze.layerHeight) / max(haze.layerWidth, 1e-3);
        vec3 piece = (realisticPlanetsHazeMain(haze, r) + haze.layer * exp(-0.5 * fromPeak * fromPeak)) * stride;
        // The optical depth toward the sun and toward the eye, held where no light gets through.
        light += piece * exp(-min(realisticPlanetsHazeTowardSun(haze, r, dot(p, sun) / r) + depth + 0.5 * piece, vec3(80.0)));
        depth += piece;
    }
    return haze.albedo * phase * light / 4.0;
}

// The body's function: its disk lit by Minnaert's law with its haze in front, where `parameters`
// are the law's, or its haze beyond the disk on its ring, where they are 0.
void realisticPlanetsHaze(inout Surface s, vec4 parameters, RealisticPlanetsHaze haze) {
    bool disk = parameters.w > 0.0;
    // The eye, the line of sight through the pixel and the sun, in the body's frame, in km,
    // stretched along the pole so that the body is round. On the texture, the pixel lies on the
    // body, whose equatorial radius in the model's units the stretched point's distance from the
    // middle gives.
    vec3 stretch = vec3(1.0, 1.0 / haze.polar, 1.0);
    vec3 local = s.local * stretch;
    float km = disk ? haze.unit / length(local) : haze.ringUnit;
    vec3 eye = objectPoint(vec3(0.0)) * stretch * km;
    vec3 ray = normalize(local * km - eye);
    vec3 toSun = objectDirection(s.toSun);
    vec3 sun = dot(toSun, toSun) > 0.5 ? normalize(toSun * stretch) : vec3(0.0);
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
