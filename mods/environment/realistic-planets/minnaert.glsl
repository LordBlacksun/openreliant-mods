// Realistic Planets (planets.luau): a planet lit as its photometry was measured, by Minnaert's law
// (limb.glsl).
//
// parameters.xyz: k for red, green and blue.
// parameters.w: the least cosine of the view the law was fitted at.

#include "limb.glsl"

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsLimb(s, parameters);
}
