// Realistic Planets (planets.luau): a planet lit as its photometry was measured, by Minnaert's law
// (limb.glsl).
//
// parameters.xyz: k for red, green and blue.
// parameters.w: the smallest cosine of the view angle that the law was fitted to.

#include "limb.glsl"

void surface(inout Surface s, vec4 parameters, float time) {
    realisticPlanetsLimb(s, parameters);
}
