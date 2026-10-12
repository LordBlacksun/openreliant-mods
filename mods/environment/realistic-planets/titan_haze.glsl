// Realistic Planets (planets.luau): Titan's haze beyond its disk, by single scattering of sunlight, as
// Cassini's frames of 2009 and 2010 show it from 28 to 164 degrees of phase. OpenReliant draws the
// function on a ring that faces the camera through Titan's middle (records.luau), in Titan's own
// frame, with Titan's radius as the unit. The mod's README describes the model and its fit, and
// sources/realistic-planets/titan/haze.py fits the numbers below and prints them.
//
// Each pixel's line of sight is followed through the haze in steps. Each step scatters the sunlight
// that reaches it toward the eye, as much as its haze's extinction, single-scattering albedo and phase
// function say, and the haze between it and the eye dims that light. The sunlight that reaches a step
// is dimmed by the main haze on its way, Chapman's integral, so the haze on Titan's night side is lit
// only high up, where the sun still reaches it past Titan's edge. Everything is worked out in the
// blue, green and red filters of Cassini's camera, in that order, and turned into the game's colours
// at the end, on the same scale as Titan's texture.

// The sphere's radius in the game, km: the haze's edge in green, where the texture's disk ends.
const float titanHazeUnit = 2741.0;
// The radius the haze's heights are measured from, the height where it is cut off, and the height
// the main haze's extinction is given at, km.
const float titanHazeBase = 2710.0;
const float titanHazeTop = 700.0;
const float titanHazeReference = 100.0;
// In each filter: the main haze's extinction at the reference height, per km, and its scale height,
// km.
const vec3 titanHazeExtinction = vec3(0.006077, 0.002138, 0.001237);
const vec3 titanHazeScale = vec3(24.2, 27.49, 30.09);
// The detached layer: its extinction at its peak, per km, and its height and width, km.
const vec3 titanHazeLayer = vec3(2.249e-05, 1.111e-05, 7.7e-06);
const vec3 titanHazeLayerHeight = vec3(318.6, 318.8, 321);
const vec3 titanHazeLayerWidth = vec3(44.9, 52, 55.2);
// The haze's single-scattering albedo, and its phase function: two Henyey-Greenstein lobes, their
// asymmetries, and the first's share of the light.
const vec3 titanHazeAlbedo = vec3(1, 0.854, 0.923);
const vec3 titanHazeFirstLobe = vec3(0.758, 0.682, 0.689);
const vec3 titanHazeSecondLobe = vec3(0.232, 0.594, 0.594);
const vec3 titanHazeFirstShare = vec3(0.556, 1, 1);
// The haze's I/F in the blue, green and red filters, in that order, to the game's linear sRGB, as
// the texture takes Titan's brightness in them (columns).
const mat3 titanHazeColour = mat3(-0.14988, 0.21081, 0.55748, 0.27673, 0.35667, -0.02695, 0.35095, -0.00266, -0.00667);
// The steps along a line of sight, spaced most closely where it passes nearest Titan.
const int titanHazeSteps = 32;
const float titanHazeSpread = 3.0;
// A pixel that spans more than half the thinnest scale height takes up to this many lines of sight
// across it, so that the haze doesn't shimmer as Titan grows small.
const int titanHazeMostSamples = 4;

// exp(y^2) erfc(y) for y >= 0, within 0.02% (a rational fit).
vec3 titanHazeErfcx(vec3 y) {
    return (1.0 + y * (0.88584516 + y * 0.31615637)) / (1.0 + y * (2.01758094 + y * (1.57175152 + y * 0.56037257)));
}

// The main haze's extinction at radius r, km, held below exp(80) deep down, where it would overflow.
vec3 titanHazeMain(float r) {
    return titanHazeExtinction * exp(min(-(r - titanHazeBase - titanHazeReference) / titanHazeScale, vec3(80.0)));
}

// The main haze's optical depth from radius r toward a direction cosChi from the vertical, out of
// the haze: Chapman's integral, the extinction at r times its scale height H times
// sqrt(pi x / 2) exp(y^2) erfc(y), with x = r / H and y = sqrt(x / 2) cosChi. Below the horizon, the
// line passes its lowest point first, and the depth is twice that from there less that back from r.
vec3 titanHazeTowardSun(float r, float cosChi) {
    vec3 here = titanHazeMain(r) * titanHazeScale * sqrt(1.5707963 * r / titanHazeScale) * titanHazeErfcx(sqrt(0.5 * r / titanHazeScale) * abs(cosChi));
    if (cosChi >= 0.0) return here;
    float lowest = r * sqrt(max(1.0 - cosChi * cosChi, 0.0));
    return 2.0 * titanHazeMain(lowest) * titanHazeScale * sqrt(1.5707963 * lowest / titanHazeScale) - here;
}

// Henyey and Greenstein's phase function of asymmetry g, at the cosine of the scattering angle.
vec3 titanHazeLobe(vec3 g, float cosTheta) {
    return (1.0 - g * g) / pow(1.0 + g * g - 2.0 * g * cosTheta, vec3(1.5));
}

// The haze's I/F in each filter along the line of sight along `ray` that passes `through` km from
// Titan's middle, nearest it toward `outward`, with the sun toward `sun`.
vec3 titanHazeLine(float through, vec3 outward, vec3 ray, vec3 sun) {
    float top = titanHazeBase + titanHazeTop;
    if (through >= top) return vec3(0.0);
    vec3 middle = outward * through;
    float chord = sqrt(top * top - through * through);
    float spacing = 1.0 / sinh(titanHazeSpread);
    vec3 depth = vec3(0.0);
    vec3 light = vec3(0.0);
    for (int i = 0; i < titanHazeSteps; i++) {
        float u = (float(i) + 0.5) / float(titanHazeSteps) * 2.0 - 1.0;
        float along = chord * sinh(titanHazeSpread * u) * spacing;
        float stride = chord * titanHazeSpread * cosh(titanHazeSpread * u) * spacing * 2.0 / float(titanHazeSteps);
        vec3 p = middle + ray * along;
        float r = length(p);
        vec3 layer = (vec3(r - titanHazeBase) - titanHazeLayerHeight) / titanHazeLayerWidth;
        vec3 extinction = titanHazeMain(r) + titanHazeLayer * exp(-0.5 * layer * layer);
        vec3 piece = extinction * stride;
        light += piece * exp(-titanHazeTowardSun(r, dot(p, sun) / r) - depth - 0.5 * piece);
        depth += piece;
    }
    float cosTheta = dot(sun, ray);
    vec3 phase = titanHazeFirstShare * titanHazeLobe(titanHazeFirstLobe, cosTheta) + (1.0 - titanHazeFirstShare) * titanHazeLobe(titanHazeSecondLobe, cosTheta);
    return titanHazeAlbedo * phase * light / 4.0;
}

void surface(inout Surface s, vec4 parameters, float time) {
    vec3 eye = objectPoint(vec3(0.0)) * titanHazeUnit;
    vec3 ray = normalize(s.local * titanHazeUnit - eye);
    vec3 sun = objectDirection(s.toSun);
    vec3 nearest = eye - dot(eye, ray) * ray;
    float through = length(nearest);
    // How far the lines of sight through the pixel spread from Titan's middle, km.
    float spread = max(fwidth(through), 1e-3);
    s.color = vec3(0.0);
    s.sunlight = vec3(0.0);
    s.glow = vec3(0.0);
    if (dot(sun, sun) < 0.5 || through < 1e-3) return;
    float thinnest = min(min(titanHazeScale.x, titanHazeScale.y), titanHazeScale.z);
    int samples = int(clamp(ceil(2.0 * spread / thinnest), 1.0, float(titanHazeMostSamples)));
    vec3 total = vec3(0.0);
    for (int k = 0; k < samples; k++) {
        float line = through + ((float(k) + 0.5) / float(samples) - 0.5) * spread;
        // A line that meets the disk takes none, but within a pixel of its edge it takes that of the
        // edge, fading, as the function runs once for each pixel and the edge's pixels show the sky
        // around the disk too.
        float share = clamp(1.0 + (line - titanHazeUnit) / spread, 0.0, 1.0);
        if (share > 0.0) total += share * titanHazeLine(max(line, titanHazeUnit), nearest / through, ray, sun);
    }
    s.glow = encoded(titanHazeColour * (total / float(samples)));
}
