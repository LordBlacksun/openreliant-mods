"""Measures how Earth's limb darkens in the game's red, green and blue, for the mod's limb function in
`planets.luau`, from two pictures of the same moment taken from two places: GOES-18's, over the
equator at 137 degrees west, and GOES-19's, at 75 west, both of 21 June 2025 at 21:00 UTC
(`goes.py`).

    python3 limb.py data

- Both pictures are binned onto latitude and longitude. Where both saw a cell, with the sun and both
  views more than `LEAST_HEIGHT` degrees above its horizon, they saw the same ground and clouds under
  the same sun, from two angles. By Minnaert's law, I/F = B mu0^k mu^(k-1), so the logarithm of the
  ratio of the two pictures' I/F is k - 1 times that of their mu's ratio, plus that of the ratio of
  B at the two phase angles. mu0 is the same in both.
- The phase angles change across each picture, and with them B, so the cells are grouped by both
  phase angles, `PHASE_BIN` degrees a group. k - 1 is the slope of the logarithm of the ratio against
  that of the mu's ratio within the groups, fitted by least squares. Cells that stray by more than
  `OUTLIER` times the spread are left out, where clouds moved or the sea glints.
- Each cell counts by its brightness, so that k follows the clouds and the land, which the eye sees
  most, more than the dark sea, whose haze brightens toward the limb.
- One picture alone won't do: Earth's ground and clouds vary far more across its disk than its limb
  darkening does, and GOES-18's disk is mostly sea in the middle, with land and clouds round its edge,
  which a fit would take for the limb brightening.
- Each channel's exponent is the one at its wavelength for a grey spectrum (`truecolour.channels`),
  interpolated along the wavelength between the two bands', and the blue band's below it.
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import goes  # noqa: E402
import truecolour as tc  # noqa: E402

data = sys.argv[1]

# The least height of the sun, and of each view above the limb, where a cell is used, degrees; the
# groups of phase angles, degrees; and how far a cell may stray from the fit, in times the median
# absolute residual.
LEAST_HEIGHT = 15.0
PHASE_BIN = 0.5
OUTLIER = 4.0

paths = sorted(glob.glob(f"{data}/OR_ABI-L2-MCMIPF-*_G1[89]_*.nc"))
(first, sun_at), (second, _) = goes.binned(paths[0]), goes.binned(paths[1])
least = np.sin(np.radians(LEAST_HEIGHT))
both = np.all([np.isfinite(first[n]) & np.isfinite(second[n]) for n in first], axis=0)
both &= (first['mu'] > least) & (second['mu'] > least) & (first['mu0'] > least) & (second['mu0'] > least)
print(f"{len(paths)} pictures; the sun over {sun_at[0]:.1f} N, {sun_at[1]:.1f} E; {both.sum()} cells seen by both")

_, group = np.unique(np.floor(first['phase'][both] / PHASE_BIN) * 1000 + np.floor(second['phase'][both] / PHASE_BIN),
                     return_inverse=True)
x = np.log(first['mu'][both] / second['mu'][both])


def within(values, weight):
    """Each cell's value less the weighted mean of its group's."""
    total = np.bincount(group, weights=weight)
    return values - (np.bincount(group, weights=weight * values) / np.maximum(total, 1e-12))[group]


exponents = []
for name, wavelength in goes.BANDS.items():
    a, b = first[name][both], second[name][both]
    keep = (a > 0) & (b > 0)
    y = np.log(np.where(keep, a / b, 1))
    brightness = np.sqrt(np.abs(a * b))
    for _ in range(4):
        weight = brightness * keep
        dx, dy = within(x, weight), within(y, weight)
        slope = np.sum(weight * dx * dy) / np.sum(weight * dx * dx)
        residual = dy - slope * dx
        keep &= np.abs(residual) < OUTLIER * np.median(np.abs(residual[keep]))
    exponents.append(slope + 1)
    print(f"{wavelength:.0f} nm: Minnaert's exponent {slope + 1:.3f}, from {keep.sum()} cells in {group.max() + 1} groups of phase angles")

lam = np.arange(380.0, 781.0, 1.0)
channels = tc.channels(lam, np.ones_like(lam), tc.matrix(lam))
limb = np.interp(channels, list(goes.BANDS.values()), exponents)
print(f"the channels' wavelengths for a grey spectrum: {np.round(channels).astype(int)} nm; their exponents, for planets.luau: "
      f"{np.round(limb, 3)}; the limb's brightness where mu is 0.25, against a plain ball's: {np.round(0.25 ** (limb - 1), 3)}")
