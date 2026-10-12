"""Fits a model of Saturn's haze to Cassini's frames of its limb at high phase, for the mod's
`saturn.glsl`, and prints the shader's numbers. Run `compose.py` first: it writes
`data/colour.json`, which turns the haze's I/F into the texture's colours.

    python3 haze.py data haze.json

The frames (`haze.json`), from Cassini's wide-angle camera in its blue, green and red filters:

- Two sets of 5 January 2009, an hour and a half apart, at 151 and 153 degrees of phase, about 33 km
  a pixel: a long stretch of the lit crescent's limb, and the haze above it.
- One set of 4 January 2013, backlit at 176 degrees, about 35 km a pixel: the haze shows as a bright
  arc round the dark disk.

The geometry:

- The sun's direction in each frame comes from the frame's geometry (`cassini.sun_direction`).
- Cassini stood about 9.3 of Saturn's radii from its middle, so it saw the edge 6 degrees off the
  middle's direction, at a phase angle of its own. Each stretch's geometry is worked out from the
  camera's place (`edges.from_afar`), and a pixel's size at the edge from the camera's distance to
  the edge (`km_per_pixel`).
- Saturn is flattened, and its outline is an ellipse (`outline_shape`): seen from the camera's
  latitude, its polar half-axis is a share of its equatorial one that the polar radius sets, and its
  long axis lies along the equator, at right angles to the north pole's direction in the frame.
  Fitted so, the 2009 frames' edges stand 58,900 to 59,400 km from the middle along the equator,
  where a circle would put them about 65,000 km out.

The measurements:

- Each frame's outline is fitted to its half-maximum edge: where, along each ray from its middle,
  the brightness falls to half way between the peak just inside it and the sky outside
  (`edges.edge_fit`). In 2009 that is the lit limb, which is the game's sphere; in 2013 it is the
  outer side of the haze's arc, which may stand up to `MOST_SHIFT` km off the sphere.
- The 2013 frames' exposures were long, and the arc's brightest pixels are saturated, as is the
  crescent in the first set of 2009: their brightest pixels pile up at one level (`ceiling`). Pixels
  above `CEILING` of that level are left out of the measurements, but not out of the edge's fit. In a
  backlit frame the arc is the haze itself, so where saturated pixels fill a bin, the fit holds the
  model at least as bright as the pile's lower side, `1 - PILE` of its level. Elsewhere below the
  arc, where light scattered more than once and the rings' light on the night side add to the
  haze's own, it holds the model at most as bright as the frame.
- The limb is cut into `SEGMENTS` stretches. In each, the sky, the median I/F between `SKY` km above
  the edge, is taken off, since the camera's stray light differs along the limb, and the I/F is
  averaged in bins of height above the edge.

The model (`scattering.py`), which the shader works out for each pixel in the same way: one haze, its
extinction falling exponentially with height, the same all round Saturn, standing for the gas and the
haze together. Its phase function is a Henyey-Greenstein lobe, taking `share` of the light, and
Rayleigh's, the gas's. The light scattered more than once isn't estimated for Saturn: the haze is
fitted with single scattering alone, and the shader draws it so. The camera blurs each frame by a
Gaussian of `BLUR` pixels, and its stray light lifts the sky near the bright limb: an exponential tail
in height, with its own length, and a constant, in each frame.

The fit, by least squares, each bin weighted by `RELATIVE` of its I/F plus `ABSOLUTE`:

- In 2009 the heights from `LIT_FITTED`, where the crescent's light, which the camera's blur spreads
  past the edge, has faded. In 2013 the heights from `BACKLIT_FITTED`, the outer side of the arc.
- The phase function's lobe and share are shared by every filter; each filter has its own extinction,
  scale height and single-scattering albedo; each frame its own stray light.
- It prints each filter's numbers, each frame's own, and the haze for `saturn.glsl`
  (`scattering.constructor`), in the order blue, green, red, with the matrix that turns the three
  filters' I/F into the texture's linear sRGB (`data/colour.json`).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import cassini  # noqa: E402
import edges  # noqa: E402
import scattering  # noqa: E402

# Saturn's equatorial and polar radii at 1 bar, km (IAU): the game's spheroid, which `build.sh`
# makes at 33.93 of the model's units a km.
UNIT = 60268.0
POLAR = 54364.0
# The unit of the ring that OpenReliant draws the haze beyond the disk on, km: half the widest span
# of Saturn's model, its rings' outer edge, 4,783,505 of the model's units (`build.sh`).
RING_UNIT = 4783505.0 / (2044626.0 / UNIT)
# The phase angle past which a frame is backlit, degrees: its edge is the outer side of the haze's
# arc rather than the lit limb.
BACKLIT = 165.0
# The measurements: the stretches of limb in a frame, the heights binned and the sky's, km above the
# edge.
SEGMENTS = 4
HEIGHTS = (-600.0, 1500.0)
SKY = (600.0, 1500.0)
# A frame is saturated where more of its pixels lie within `PILE` of its 99.9th percentile than in
# the band of the same width below; its pixels brighter than `CEILING` of that level are left out.
PILE = 0.05
CEILING = 0.85
# The model: the height the extinction is given at, km above `UNIT`; the height the haze is cut off
# at; the steps along a line of sight, closest where it passes nearest Saturn; and the camera's blur,
# pixels.
REFERENCE = 100.0
TOP = 1000.0
STEPS, SPREAD = 96, 3.0
BLUR = 0.6
# The fit: the heights fitted in a lit frame and in a backlit one, km above the edge; each bin's
# weight; how far a backlit frame's edge may stand off the game's sphere, km; the least pixels a bin
# needs; and the most evaluations.
LIT_FITTED = (90.0, 400.0)
BACKLIT_FITTED = (0.0, 400.0)
RELATIVE, ABSOLUTE = 0.05, 3e-4
MOST_SHIFT = 400.0
LEAST_PIXELS = 6
MOST_EVALUATIONS = 400
# The filters, their own numbers, first guesses and bounds: the extinction at `REFERENCE` (its
# logarithm, per km), the scale height (km) and the single-scattering albedo.
FILTERS = ['BL1', 'GRN', 'RED']
OWN_FILTER = ['log extinction', 'scale height', 'albedo']
FILTER_FIRST_GUESS = [np.log(1e-4), 50.0, 0.9]
FILTER_LOWEST = [-25.0, 5.0, 0.05]
FILTER_HIGHEST = [3.0, 200.0, 1.0]
# The phase function's lobe's asymmetry and share, shared by every filter.
SHARED = ['lobe', 'share']
SHARED_FIRST_GUESS = [0.7, 0.9]
SHARED_LOWEST = [0.0, 0.0]
SHARED_HIGHEST = [0.98, 1.0]
# Each frame's own: its edge's shift (km), its stray light's tail and the tail's length (km), and a
# constant; the first guesses and bounds of the tail and the constant. The camera's stray light
# spreads over tens of pixels, so the tail is at least `SHORTEST_TAIL` pixels and `SHORTEST_TAIL_KM`
# long, and can't stand in for the haze, which falls off within a few.
OWN_FRAME = ['shift', 'tail', 'length', 'offset']
FRAME_FIRST_GUESS = [1e-3, 0.0]
FRAME_LOWEST = [0.0, -0.02]
FRAME_HIGHEST = [0.5, 0.02]
SHORTEST_TAIL = 30.0
SHORTEST_TAIL_KM = 100.0
LONGEST_TAIL_KM = 3000.0
# How much of the haze's light blooms, which the mod chooses rather than the fit: a quarter, as for
# Titan's and Neptune's.
BLOOM = 0.25


def km_per_pixel(f):
    """A frame's pixel at Saturn's edge, km: its size at the middle's distance, which OPUS gives,
    times the camera's distance to the edge over its distance to the middle."""
    return f['resolution_km'] * np.sqrt(1 - (UNIT / f['distance_km']) ** 2)


def outline_shape(f):
    """Saturn's outline in a frame (`edges.flattened`): its polar half-axis as a share of its
    equatorial one, seen from the camera's latitude, and the equator's angle from right toward up,
    at right angles to the north pole's, which lies its clock angle round from up."""
    latitude = np.radians(f['observer_lat'])
    flattening = 1 - (POLAR / UNIT) ** 2
    return np.sqrt(1 - flattening * np.cos(latitude) ** 2), -np.radians(f['north_clock_angle'])


def ceiling(image):
    """The level a frame's brightest pixels pile up at where the camera saturated, or infinity where
    they don't."""
    level = np.nanpercentile(image, 99.9)
    near = np.count_nonzero((image >= (1 - PILE) * level) & (image < (1 + PILE) * level))
    below = np.count_nonzero((image >= (1 - 3 * PILE) * level) & (image < (1 - PILE) * level))
    return level if near > below else np.inf


def measure(data, f):
    """A frame's limb, in `SEGMENTS` stretches: each one's I/F over its sky averaged in bins of height
    above the edge, with the pixels in each bin, its angle round from the sun's direction, and its
    edge as a view from afar shows it (`edges.from_afar`)."""
    image = cassini.frame(os.path.join(data, os.path.basename(f['urls'][1])))
    image = np.where(np.isfinite(image) & (image < cassini.MOST_IF), image, np.nan)
    km = km_per_pixel(f)
    shape = outline_shape(f)
    guess = edges.edge_guess(image, UNIT / km, shape)
    (cx, cy, r), points, angles, rms = edges.edge_fit(image, guess, shape)
    level = ceiling(image)
    saturated = image >= CEILING * level
    measured = np.where(saturated, np.nan, image)
    backlit = f['phase'] > BACKLIT
    lines, samples = np.indices(image.shape).astype(np.float64)
    x, y = samples - cx, cy - lines
    height = edges.above(x, y, r, shape) * km
    sun = cassini.sun_direction(f)
    # The stretches: the middle of the edge's span, round from its middle.
    middle = np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))
    spread = np.angle(np.exp(1j * (angles - middle)))
    low, high = np.percentile(spread, [10, 90])
    turn = np.angle(np.exp(1j * (np.arctan2(y, x) - middle)))
    bins = np.arange(HEIGHTS[0], HEIGHTS[1] + km, km)
    stretches = []
    for k in range(SEGMENTS):
        start, end = low + (high - low) * k / SEGMENTS, low + (high - low) * (k + 1) / SEGMENTS
        along = np.isfinite(measured) & (turn >= start) & (turn < end)
        heights, mean, count = edges.binned(measured, height, along & (height >= bins[0]) & (height < bins[-1]), bins)
        # The bins that saturated pixels fill, as a share of all the stretch's pixels in each.
        everywhere = np.isfinite(image) & (turn >= start) & (turn < end) & (height >= bins[0]) & (height < bins[-1])
        _, filled, _ = edges.binned(saturated.astype(np.float64), height, everywhere, bins)
        # Partly saturated bins are short of their saturated pixels' light.
        mean = np.where(filled > 0, np.nan, mean)
        # Below a backlit frame's edge, the haze's single scattering is at least as bright as the pile's
        # lower side where saturated pixels fill a bin, and at most as bright as the frame elsewhere.
        inner = backlit & (heights < BACKLIT_FITTED[0])
        least = np.where(inner & (filled >= 0.5), (1 - PILE) * level, np.nan)
        most = np.where(inner & np.isfinite(mean) & (count >= LEAST_PIXELS), mean, np.nan)
        sky = np.median(measured[along & (height >= SKY[0]) & (height < SKY[1])])
        angle = np.degrees(np.angle(np.exp(1j * (middle + (start + end) / 2 - sun))))
        phase, afar = edges.from_afar(UNIT, f['distance_km'], f['phase'], angle)
        stretches.append(dict(heights=heights, mean=mean - sky, count=count, least=least - sky, most=most - sky, angle=afar,
                              phase=phase, round=angle, sky=sky))
    print(f"{f['name']} ({f['filter']}, {f['phase']:.1f} degrees, {km:.2f} km a pixel): edge rms {rms:.2f} px over "
          f"{len(points)} points, {r * km:.0f} km along the equator; "
          + (f"saturated at {level:.4f}" if np.isfinite(level) else "not saturated") + "; stretches "
          + ', '.join(f"{s['round']:.0f}" for s in stretches) + " degrees round from the sun's direction, at "
          + ', '.join(f"{s['phase']:.1f}" for s in stretches) + " degrees of phase, skies "
          + ', '.join(f"{s['sky']:.4f}" for s in stretches))
    return dict(name=f['name'], filter=f['filter'], phase=f['phase'], km=km, stretches=stretches,
                fitted=BACKLIT_FITTED if backlit else LIT_FITTED)


def haze_of(own_filter, shared):
    """A filter's haze as the model takes it (`scattering.Haze`): one lobe and Rayleigh's."""
    log_extinction, scale, albedo = own_filter
    lobe, share = shared
    return scattering.Haze(UNIT + REFERENCE, log_extinction, scale, albedo, (lobe, 0.0, share, 0.0), UNIT + TOP, UNIT)


def most_shift(m):
    """How far a frame's edge may stand off the game's sphere, km: up to `MOST_SHIFT` for a backlit
    frame, and within a hair of it for a lit one, as the bounds must stand apart."""
    return MOST_SHIFT if m['phase'] > BACKLIT else 1e-6


if __name__ == '__main__':
    data, listing = sys.argv[1:3]
    with open(listing) as f:
        frames = json.load(f)['frames']
    with open(os.path.join(data, 'colour.json')) as f:
        colours = json.load(f)['colours']
    measured = [measure(data, f) for f in frames]
    fitted, result = edges.fit(measured, {name: None for name in FILTERS}, sys.modules[__name__])
    shared, filters, owns = fitted
    edges.describe(measured, fitted, result, sys.modules[__name__])
    numbers = np.array([filters[name] for name in FILTERS]).T
    lobe, share = shared
    # The texture's phase: Hubble's and Cassini's maps take the light's angle out, so it shows Saturn
    # as from the sun, at no phase.
    print('for saturn.glsl:')
    print(scattering.constructor(
        'saturnHaze', UNIT, UNIT + REFERENCE, UNIT + TOP, np.exp(numbers[0]), numbers[1], [0.0] * 3, [UNIT] * 3, [1.0] * 3,
        -1.0, numbers[2], [lobe] * 3, [0.0] * 3, [share] * 3, [0.0] * 3, None, [colours[name] for name in FILTERS], BLOOM,
        polar=POLAR / UNIT, ring_unit=RING_UNIT))
