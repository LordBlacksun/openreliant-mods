"""Composes the texture of Saturn's rings: a strip of 4096 by 8 RGBA texels, its width running out from
radius `INNER` to `OUTER`, every row alike, for the ring that `sphere.py` writes.

    python3 rings.py data globe.png out.png <key light blue>

- The alpha is the share of the light the rings stop seen face on, 1 - exp(-tau), from the normal
  optical depth tau that Voyager 2's photopolarimeter measured as the rings passed in front of the star
  delta Scorpii in August 1981, at 10 km a sample (PDS volume VG_2801). The ring's surface function
  works out from it the share they stop seen at any angle.
- The brightness is the reflectance of the ring's particles, from the lit side's brightness that
  Voyager 2's narrow-angle camera measured on its finest mosaic of the rings, also in August 1981, at
  10 km a sample (VG_2810), with the sun 8.05 degrees above the rings and the camera 23.3 degrees
  above them. Light scattered once in a layer of optical depth tau gives
  I/F = S mu0 / (mu + mu0) (1 - exp(-tau (1/mu + 1/mu0))), where S is the particles' albedo times their
  phase function over 4, so S is the measured I/F over the rest. Where the rings are too thin for that
  to tell, S is interpolated from either side. The F ring lies past the mosaic and takes the outer A
  ring's.
- The hue is that of Cassini's natural colour mosaic across the lit rings (PIA11142, November 2008),
  in linear light, smoothed over `HUE_SMOOTH` km. The mosaic shows the rings as arcs about Saturn's
  centre; it is read along the line through the arcs' turning points, where its columns run along the
  radius, and its columns are put at their radii by the ring edges that both it and Voyager's mosaic
  show sharply.
- The ring's brightness is tied to the planet's: the B ring at its brightest, seen and lit from the
  same height, is as bright as Saturn's equatorial zone in the planet's texture seen and lit from
  overhead, as the two look about alike from Earth. `globe.png` is the planet's texture, and `key
  light blue` the factor its blue was divided by.
"""
import subprocess
import sys

import numpy as np
from scipy import ndimage

data, globe, out, key_blue = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])

# The strip's radii, km, and size in texels.
INNER, OUTER = 74000.0, 141000.0
SIZE = (4096, 8)
# The geometry of Voyager 2's mosaic of the lit rings, from its label: the cosines of the sun's and the
# camera's angles from the rings' pole.
SUN = np.cos(np.radians(81.95))
VIEW = np.cos(np.radians(66.7))
# Where the layer stops too little light for its brightness to give the particles' reflectance, the
# km the reflectance is smoothed over, and where it stops enough for the reflectance to be sure, whose
# highest values bound it elsewhere: where an edge that isn't round, such as the B ring's outer edge,
# stands at different radii in the two profiles.
LEAST_STOPPED = 0.1
REFLECTANCE_SMOOTH = 50.0
SURE_STOPPED = 0.5
HIGHEST = 0.995
# The A ring's outer part, whose reflectance the F ring takes, km.
OUTER_A = (135000.0, 136700.0)
# The equatorial zone's latitudes in the planet's texture, and how many times its brightness the B ring
# at its brightest takes, as seen from the same height and lit from overhead: once at the disk's
# middle, where mu = mu0 = 1, against a layer seen and lit from the same height, which gives S / 2.
EQUATORIAL_ZONE = 15.0
B_RING = (99000.0, 117500.0)
BRIGHTEST = 0.9
# Cassini's mosaic: where to look for the C ring's inner edge and the A ring's outer edge along each
# row, the rows sampled about the line through the arcs' turning points, the darkest it is read where
# the rings are, and the km its hue is smoothed over.
MOSAIC_C_EDGE = (0, 4000, 0.01)
MOSAIC_A_EDGE = (9500, 11300, 0.05)
MOSAIC_ROWS = 15
MOSAIC_DARKEST = 0.01
HUE_SMOOTH = 300.0
# The ring edges that both mosaics show sharply, at about these radii, km, rising or falling outward:
# first the three that stand out most, the C ring's inner edge, the B ring's outer edge and the A
# ring's outer edge, found within `FIRST_REACH` columns of a straight scale between the outer two, then
# the others within `NEXT_REACH` columns of a parabola through those three.
FIRST_EDGES = [(74490, 1), (117570, -1), (136770, -1)]
NEXT_EDGES = [(77750, -1), (87340, -1), (91980, 1), (122050, 1), (133420, -1)]
FIRST_REACH = 300
NEXT_REACH = 40


def table(path):
    """A PDS ring profile's rows."""
    with open(path) as rows:
        return np.array([[float(v) for v in row.split(',')] for row in rows if row.strip()])


def steepest(x, y, centre, half, sign, smooth):
    """Where the logarithm of `y` rises most (or falls most, for a negative `sign`) within `half` of
    `centre`."""
    slope = sign * np.gradient(ndimage.gaussian_filter1d(np.log(np.maximum(y, 1e-5)), smooth))
    near = (x >= centre - half) & (x <= centre + half)
    return x[near][np.argmax(slope[near])]


def luminance(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def decoded(srgb):
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def read(path):
    """A picture's pixels in linear light, rows first."""
    w, h = map(int, subprocess.run(['magick', 'identify', '-format', '%w %h', path], capture_output=True, text=True,
                                   check=True).stdout.split())
    raw = subprocess.run(['magick', path, '-depth', '16', 'rgb:-'], capture_output=True, check=True).stdout
    return decoded(np.frombuffer(raw, '<u2').reshape(h, w, 3).astype(np.float64) / 65535)


# The strip's texels.
w, h = SIZE
radii = INNER + (np.arange(w) + 0.5) * (OUTER - INNER) / w

# The transmission seen face on, exp(-tau), from the occultation: none where the star was lost, and
# averaged over each texel, from the samples interpolated a kilometre apart.
pps = table(f"{data}/PS1P01.TAB")
r_pps, tau = pps[:, 0], pps[:, 3]
through = np.where(tau >= 99, 0.0, np.exp(-np.clip(tau, 0, None)))
km = np.arange(INNER, OUTER + 1)
total = np.concatenate([[0], np.cumsum(np.interp(km[:-1] + 0.5, r_pps, through, left=1.0, right=1.0))])
bounds = INNER + np.arange(w + 1) * (OUTER - INNER) / w
passed = np.diff(np.interp(bounds, km, total)) / np.diff(bounds)
alpha = 1 - passed

# The particles' reflectance from the lit side's brightness.
iss = table(f"{data}/IS2_P0001_V01_KM010.TAB")
r_iss, brightness = iss[:, 0], iss[:, 1]
stopped = 1 - np.interp(r_iss, r_pps, through) ** (1 / VIEW + 1 / SUN)
reflectance = np.where(stopped > LEAST_STOPPED, brightness * (VIEW + SUN) / SUN / np.maximum(stopped, LEAST_STOPPED), np.nan)
known = np.isfinite(reflectance)
reflectance = np.interp(r_iss, r_iss[known], reflectance[known])
reflectance = ndimage.median_filter(reflectance, size=int(round(REFLECTANCE_SMOOTH / 10)) | 1)
reflectance = np.minimum(reflectance, np.quantile(reflectance[stopped > SURE_STOPPED], HIGHEST))
outer_a = np.median(reflectance[(r_iss >= OUTER_A[0]) & (r_iss <= OUTER_A[1])])
S = np.interp(radii, r_iss, reflectance, right=outer_a)
for name, (a, b) in (('C ring', (74500, 92000)), ('B ring', (92000, 117500)), ('Cassini Division', (117600, 122000)),
                     ('A ring', (122100, 136700))):
    inside = (radii >= a) & (radii < b)
    print(f"{name}: optical depth seen face on, median {np.median(-np.log(np.maximum(passed[inside], 1e-6))):.2f}; "
          f"the particles' reflectance S, median {np.median(S[inside]):.3f}")

# Cassini's mosaic: the line through the arcs' turning points, where the C ring's inner edge and the A
# ring's outer edge turn.
mosaic = read(f"{data}/PIA11142.tif")
L = luminance(mosaic)
rows = np.nonzero((L > MOSAIC_C_EDGE[2]).any(axis=1))[0]
rows = np.arange(rows.min() + 20, rows.max() - 20)


def turning(first, last, threshold, outward):
    """Where the edge that each row first (or last) passes `threshold` between columns `first` and
    `last` turns: the column and row of the parabola's vertex through those points."""
    xs = []
    for y in rows:
        above = np.nonzero(L[y, first:last] > threshold)[0]
        xs.append(first + (above[-1] if outward else above[0]) if len(above) else np.nan)
    xs = np.array(xs)
    ok = np.isfinite(xs)
    p = np.polyfit(rows[ok], xs[ok], 2)
    y = -p[1] / (2 * p[0])
    return np.polyval(p, y), y


inner_x, inner_y = turning(*MOSAIC_C_EDGE, outward=False)
outer_x, outer_y = turning(*MOSAIC_A_EDGE, outward=True)
x = np.arange(mosaic.shape[1])
line = inner_y + (x - inner_x) * (outer_y - inner_y) / (outer_x - inner_x)
band = np.mean([mosaic[np.clip(np.round(line + dy).astype(int), 0, mosaic.shape[0] - 1), x]
                for dy in range(-MOSAIC_ROWS, MOSAIC_ROWS + 1)], axis=0)
print(f"Cassini's mosaic read along the line from column {inner_x:.0f}, row {inner_y:.0f} to column {outer_x:.0f}, "
      f"row {outer_y:.0f}")

# Its columns at their radii: each sharp edge found in Voyager's mosaic, then in Cassini's near where
# the scale so far puts it.
def matched(edges, column_at, reach):
    found = []
    for radius, sign in edges:
        at = steepest(r_iss, brightness, radius, 250, sign, 1.0)
        found.append((steepest(x.astype(float), luminance(band), column_at(at), reach, sign, 1.5), at))
    return found


first_edge = steepest(r_iss, brightness, FIRST_EDGES[0][0], 250, FIRST_EDGES[0][1], 1.0)
last_edge = steepest(r_iss, brightness, FIRST_EDGES[-1][0], 250, FIRST_EDGES[-1][1], 1.0)
anchors = matched(FIRST_EDGES, lambda at: inner_x + (at - first_edge) * (outer_x - inner_x) / (last_edge - first_edge),
                  FIRST_REACH)
curve = np.polyfit([a for _, a in anchors], [c for c, _ in anchors], 2)
anchors = np.array(sorted(anchors + matched(NEXT_EDGES, lambda at: np.polyval(curve, at), NEXT_REACH)))
assert np.all(np.diff(anchors, axis=0) > 0), anchors
scale = np.diff(anchors[:, 1]) / np.diff(anchors[:, 0])
print(f"Cassini's mosaic: {len(anchors)} edges matched, {scale.min():.2f} to {scale.max():.2f} km a column")
# The column at each texel's radius, carried on past the outer edges at their segments' scales.
columns = np.interp(radii, anchors[:, 1], anchors[:, 0])
columns = np.where(radii < anchors[0, 1], anchors[0, 0] + (radii - anchors[0, 1]) / scale[0], columns)
columns = np.where(radii > anchors[-1, 1], anchors[-1, 0] + (radii - anchors[-1, 1]) / scale[-1], columns)

# The hue at each texel, where the mosaic shows the rings, interpolated across the gaps and smoothed.
sampled = np.stack([np.interp(columns, x, band[:, c]) for c in range(3)], axis=-1)
lum = luminance(sampled)
shown = lum > MOSAIC_DARKEST
hue = np.stack([np.interp(radii, radii[shown], sampled[shown, c] / lum[shown]) for c in range(3)], axis=-1)
hue = ndimage.gaussian_filter1d(hue, HUE_SMOOTH / ((OUTER - INNER) / w), axis=0, mode='nearest')
hue /= luminance(hue)[:, None]

# The planet's equatorial zone, in its own colours.
planet = read(globe)
planet[..., 2] *= key_blue
latitudes = 90 - (np.arange(planet.shape[0]) + 0.5) * 180 / planet.shape[0]
zone = np.abs(latitudes) <= EQUATORIAL_ZONE
weights = np.cos(np.radians(latitudes[zone]))[:, None]
equatorial = np.sum(luminance(planet[zone]) * weights) / (weights.sum() * planet.shape[1])

# The B ring at its brightest, seen and lit from the same height, which gives S / 2, as bright as the
# equatorial zone seen and lit from overhead.
b_ring = (radii >= B_RING[0]) & (radii <= B_RING[1])
gain = 2 * equatorial / np.quantile(S[b_ring], BRIGHTEST)
colour = gain * S[:, None] * hue
print(f"the planet's equatorial zone: {equatorial:.3f}; the particles' reflectance in the texture: B ring "
      f"{np.median(colour[b_ring] @ np.array([0.2126, 0.7152, 0.0722])):.3f}")
fit = colour.max()
assert fit <= 1, f"the ring's colour reaches {fit:.2f}"

rgba = np.concatenate([colour, alpha[:, None]], axis=1)
pixels = (np.clip(np.broadcast_to(rgba, (h, w, 4)), 0, 1) * 65535 + 0.5).astype('<u2')
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '16', '-endian', 'LSB', 'rgba:-', '-set', 'colorspace', 'RGB',
                '-colorspace', 'sRGB', '-depth', '8', '-define', 'png:exclude-chunks=date,time', f'PNG32:{out}'],
               input=pixels.tobytes(), check=True)
print('wrote', out)
