"""A haze's particles through Mie theory, for the bodies whose haze is built from measurements of its
particles rather than fitted to frames of the limb (`venus/haze.py`, `jupiter/haze.py`): a log-normal
spread of spheres' cross-sections and phase function, by S. Prahl's miepython, and the model's phase
function fitted to it.
"""
import miepython
import numpy as np
from scipy import optimize

import scattering

# The radii a spread of sizes is summed over: `RADII` of them, over `REACH` of its log-normal's widths
# either side of its middle.
RADII = 200
REACH = 4.0
# The phase function's fit: the angles from the forward direction that count `FORWARD_WEIGHT` times
# as much, degrees, where a backlit haze's light comes from; and the first guesses it starts from,
# the best of which it keeps, and the bounds: the lobes' asymmetries, the first's share, and the
# second's share of what the first leaves.
FORWARD = 30.0
FORWARD_WEIGHT = 3.0
FIRST_GUESSES = [(0.9, 0.5, 0.2, 0.9), (0.95, 0.6, 0.1, 0.8), (0.8, 0.0, 0.5, 0.5), (0.7, -0.3, 0.8, 0.5)]
LOWEST = (0.0, -0.95, 0.0, 0.0)
HIGHEST = (0.995, 0.95, 1.0, 1.0)


def particles(radius, variance, index, wavelength):
    """Spheres of effective radius `radius`, micrometres, spread as a log-normal of effective variance
    `variance`, of refractive index `index`, at `wavelength` nm: each one's mean extinction and
    scattering cross-section, square micrometres, and their phase function at every degree from 0 to
    180, in `scattering.phase_function`'s normalisation."""
    width = np.sqrt(np.log(1 + variance))
    middle = radius / (1 + variance) ** 2.5
    logs = np.linspace(np.log(middle) - REACH * width, np.log(middle) + REACH * width, RADII)
    weights = np.exp(-0.5 * ((logs - np.log(middle)) / width) ** 2)
    weights /= weights.sum()
    mu = np.cos(np.radians(np.arange(181.0)))
    extinction = scattered = 0.0
    phase = np.zeros(181)
    for r, weight in zip(np.exp(logs), weights):
        q_ext, q_sca, _, _ = miepython.efficiencies(index, 2 * r, wavelength / 1000)
        area = np.pi * r * r
        extinction += weight * area * q_ext
        scattered += weight * area * q_sca
        phase += weight * area * q_sca * miepython.i_unpolarized(index, 2 * np.pi * r * 1000 / wavelength, mu, norm='4pi')
    return extinction, scattered, phase / scattered


def lobes(phase):
    """The model's phase function that best follows `phase`, at every degree from 0 to 180, on its
    logarithm: two Henyey-Greenstein lobes' asymmetries and their shares of the light, Rayleigh's
    taking the rest. It follows a haze of small spheres within about 10% within `FORWARD` degrees of
    the forward direction, and within 20 to 30% elsewhere, short of a glory near the backward one."""
    angles = np.arange(181.0)
    cos = np.cos(np.radians(angles))
    weight = np.where(angles <= FORWARD, FORWARD_WEIGHT, 1.0)

    def shares(p):
        # The second's share is of what the first leaves, so that the two never pass 1.
        return p[2], (1 - p[2]) * p[3]

    def residuals(p):
        return weight * np.log(scattering.phase_function(cos, p[0], p[1], *shares(p)) / phase)

    best = min((optimize.least_squares(residuals, start, bounds=(LOWEST, HIGHEST)) for start in FIRST_GUESSES), key=lambda fit: fit.cost)
    return best.x[0], best.x[1], *shares(best.x)
