"""Makes the figures of the note on Neptune's map, `neptune.typ`, from the build's working files, and
prints the numbers the note quotes, so that a new build can be checked against its text. They come
from the Voyager frames and the scripts alone; nothing of the game's goes into them.

    python3 figures.py ../neptune true-colour.png shipped.png figures

`true-colour.png` is the map composed without the contrast stretch and the key light's correction,
`shipped.png` the mod's texture.
"""
import json
import os
import subprocess
import sys
from collections import defaultdict

import numpy as np

neptune, true_colour, shipped, out = sys.argv[1:5]
sys.path[:0] = [os.path.abspath(neptune), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
import nepgeo  # noqa: E402
import render  # noqa: E402
import truecolour as tc  # noqa: E402
import voyager  # noqa: E402

frames = {f['name']: f for f in json.load(open(f"{neptune}/frames.json"))['frames']}
fits = json.load(open(f"{neptune}/fits.json"))
twists = json.load(open(f"{neptune}/twists.json"))
luminance = np.load(f"{neptune}/maps/luminance.npz")
os.makedirs(out, exist_ok=True)

# The frame drawn with its fitted grid: a clear frame of 20 August, with the Great Dark Spot in view.
FRAME = 'C1124452'
GRID, EQUATOR, PRIME = 'rgba(255,255,255,0.55)', 'rgb(60,220,130)', 'rgb(255,210,0)'
BLEMISH = 'rgb(235,50,40)'
# Where a map has no data.
NO_DATA = (0.35, 0.06, 0.06)
# The latitudes over which the mosaics' means are taken, as in `compose.py`.
WELL_SEEN = (-60, 20)


def write(pixels, path, strokes=()):
    """Writes display values from 0 to 1, RGB (h, w, 3), as an 8-bit picture, with polylines drawn
    over it by ImageMagick, each a colour, a width and its points."""
    pixels = np.round(np.clip(pixels, 0, 1) * 255).astype(np.uint8)
    h, w = pixels.shape[:2]
    command = ['magick', '-size', f'{w}x{h}', '-depth', '8', 'rgb:-']
    mvg = path + '.mvg'
    if strokes:
        lines = ['fill none', 'stroke-linecap round', 'stroke-linejoin round']
        for colour, width, points in strokes:
            lines += [f"stroke '{colour}'", f'stroke-width {width}', 'polyline ' + ' '.join(f'{x:.2f},{y:.2f}' for x, y in points)]
        with open(mvg, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        command += ['-draw', f'@{mvg}']
    try:
        subprocess.run(command + ['-quality', '90', path], input=pixels.tobytes(), check=True)
    finally:
        if strokes:
            os.remove(mvg)


def stack(parts, axis=0, gap=24, background=1.0):
    """Pictures one above the other (axis 0) or side by side (axis 1), with a margin between them."""
    shape = list(parts[0].shape)
    shape[axis] = gap
    margin = np.full(shape, background)
    joined = [parts[0]]
    for part in parts[1:]:
        joined += [margin, part]
    return np.concatenate(joined, axis=axis)


def halve(a):
    """A map at half the size, each cell the mean of the four it covers that hold data."""
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    b = a[:h, :w].reshape(h // 2, 2, w // 2, 2)
    seen = np.isfinite(b)
    n = seen.sum(axis=(1, 3))
    return np.where(n > 0, np.where(seen, b, 0).sum(axis=(1, 3)) / np.maximum(n, 1), np.nan)


def north_up(a):
    """A mosaic, south first and 0 east first, turned north up with 0 east in the middle, as the
    texture is."""
    return np.roll(a[::-1], a.shape[1] // 2, axis=1)


def resized(path, width, height):
    """A picture read as linear RGB and resized in linear light."""
    raw = subprocess.run(['magick', path, '-colorspace', 'RGB', '-filter', 'Lanczos', '-resize', f'{width}x{height}!',
                          '-depth', '16', 'rgb:-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='<u2').reshape(height, width, 3) / 65535.0


def frame_figure():
    frame, fit = frames[FRAME], fits[FRAME]
    img, _ = voyager.image(f"{neptune}/data/{FRAME}_GEOMED.IMG", f"{neptune}/data/{FRAME}_GEOMED.LBL")
    view = nepgeo.view(frame, fit['cx'], fit['cy'], fit['twist'], fit['scale'])
    # Darker mid-tones bring out the clouds on the bright disk.
    shown = np.clip(img / np.percentile(img[img > 0.02], 99.9), 0, 1) ** 1.8
    # Cropped to the disk, with a margin.
    half = int(1.08 * fit['scale'] * nepgeo.NEPTUNE.a / frame['distance_km'] / nepgeo.PIXEL)
    x0, y0 = int(round(fit['cx'])) - half, int(round(fit['cy'])) - half
    shown = np.pad(shown, half)[y0 + half:y0 + 3 * half, x0 + half:x0 + 3 * half]
    grid, marked = [], []

    def line(lats, lons, strokes, colour, width):
        p = nepgeo.NEPTUNE.surface(lats, lons)
        mu, _ = view.angles(p)
        x, y = view.project(p)
        x, y = x - x0, y - y0
        # Each run of points on the side facing the camera is one polyline.
        ends = np.flatnonzero(np.diff(np.concatenate([[0], (mu > 0).astype(int), [0]])))
        for a, b in zip(ends[::2], ends[1::2]):
            if b - a > 1:
                strokes.append((colour, width, list(zip(x[a:b], y[a:b]))))

    around, along = np.arange(0, 360.01, 0.5), np.arange(-90, 90.01, 0.5)
    for lat in range(-75, 76, 15):
        line(np.full_like(around, lat), around, *((marked, EQUATOR, 3) if lat == 0 else (grid, GRID, 1.5)))
    for lon in range(0, 360, 15):
        line(along, np.full_like(along, lon), *((marked, PRIME, 3) if lon == 0 else (grid, GRID, 1.5)))
    write(np.repeat(shown[..., None], 3, axis=2), f"{out}/frame.jpg", grid + marked)


def blemish_figure():
    pattern = np.load(f"{neptune}/pattern.npy")
    spread = 1.4826 * np.median(np.abs(pattern[pattern != 0]))
    turn = np.deg2rad(np.arange(0, 360.1, 5))
    rings = [(BLEMISH, 3, list(zip(x + 45 * np.cos(turn), y + 45 * np.sin(turn)))) for x, y in nepgeo.BLEMISHES]
    write(np.repeat(np.clip(0.5 + pattern / (8 * spread), 0, 1)[..., None], 3, axis=2), f"{out}/blemishes.jpg", rings)


def calibration_figure():
    """The luminance mosaic before and after the self-calibration, from 80 south to 50 north."""
    lats = luminance['lats']
    mean = np.nanmean(luminance['albedo'][(lats > WELL_SEEN[0]) & (lats < WELL_SEEN[1])])
    shown_lats = lats[:lats.size // 2 * 2].reshape(-1, 2).mean(axis=1)
    rows = (shown_lats > -80) & (shown_lats < 50)
    parts = []
    for a in (luminance['uncalibrated'], luminance['albedo']):
        shown = np.clip(0.5 + 2.5 * (halve(a)[rows] / mean - 1), 0, 1)
        rgb = np.where(np.isfinite(shown)[..., None], np.repeat(np.nan_to_num(shown)[..., None], 3, axis=2), NO_DATA)
        parts.append(north_up(rgb))
    write(stack(parts), f"{out}/calibration.jpg")


def maps_figure():
    render.save(stack([resized(true_colour, 1800, 900), resized(shipped, 1800, 900)]), f"{out}/maps.jpg")


def features():
    """Where the largest storms are on the map: the Great Dark Spot, the Scooter and the second dark
    spot, as the darkest or brightest place, smoothed, in their bands."""
    a, lats, lons = luminance['albedo'], luminance['lats'], luminance['lons']
    smooth = voyager.smooth(a, 1.0, lats[1] - lats[0])
    found = {}
    for name, (south, north, darkest) in {'Great Dark Spot': (-28, -14, True), 'Scooter': (-46, -38, False),
                                          'Dark Spot 2': (-60, -48, True)}.items():
        rows = (lats > south) & (lats < north)
        band = smooth[rows]
        r, c = np.unravel_index(np.nanargmin(band) if darkest else np.nanargmax(band), band.shape)
        found[name] = (float(lats[rows][r]), float(lons[c]))
    return found


def views_figure(spots):
    """Views from 25 degrees south, lit from 15 degrees east of the viewer: facing the Great Dark
    Spot, the second dark spot, and the side away from both. They are drawn at twice the size and
    averaged down, so that the texture doesn't alias."""
    great, second = spots['Great Dark Spot'][1], spots['Dark Spot 2'][1]
    between = (great + second) / 2 + (180 if abs(great - second) < 180 else 0)
    size, rows = 400, []
    for path, light in ((true_colour, (1.0, 1.0, 1.0)), (shipped, (1.0, 1.0, 0.8))):
        texture = render.load(path)
        row = []
        for lon in (great, second, between):
            big = render.render(texture, 2 * size, -25, lon, -26, lon + 15, 0.75, light)
            row.append(big.reshape(size, 2, size, 2, 3).mean(axis=(1, 3)))
        rows.append(stack(row, axis=1, gap=12))
    render.save(stack(rows, gap=12), f"{out}/views.jpg")


def twist_figure():
    """Each frame's cost curve, thin, each day's mean, thick, and each day's twist, dashed, as a
    pgfplots picture that the note includes, so that its type matches the text's."""
    xs = np.array(twists['twists_deg'])
    by_day = defaultdict(list)
    for name, curve in twists['curves'].items():
        by_day[frames[name]['time'][:10]].append(np.array(curve))
    every = np.concatenate([c for cs in by_day.values() for c in cs])
    ylo, yhi = np.floor(every.min() * 5) / 5, np.ceil(every.max() * 5) / 5
    colours = {'1989-08-17': 'dayone', '1989-08-20': 'daytwo'}

    def coordinates(values, at=xs):
        return ' '.join(f'({x:g},{y:.4f})' for x, y in zip(at, values))

    lines = [r'\begin{tikzpicture}',
             r'\begin{axis}[width=0.8\textwidth, height=0.42\textwidth, xmin=-25, xmax=10, '
             rf'ymin={ylo:.1f}, ymax={yhi:.1f}, xlabel={{Trial roll angle $\theta$ (degrees)}}, '
             r'ylabel={$C(\theta)/\langle C\rangle$}, legend pos=north east, legend cell align=left, '
             r'tick label style={font=\small}, label style={font=\small}, legend style={font=\small}]']
    for day, curves in sorted(by_day.items()):
        lines += [rf'\addplot[{colours[day]}, opacity=0.3, line width=0.3pt, forget plot] coordinates {{{coordinates(c)}}};'
                  for c in curves]
    for day, curves in sorted(by_day.items()):
        lines += [rf'\addplot[{colours[day]}, line width=1.2pt] coordinates {{{coordinates(np.mean(curves, axis=0))}}};',
                  rf'\addlegendentry{{{int(day[8:])} August, {len(curves)} images}}']
    for day in sorted(by_day):
        roll = twists['days'][day]
        lines.append(rf'\addplot[{colours[day]}, dashed, forget plot] coordinates {{{coordinates([ylo, yhi], [roll, roll])}}};')
    lines += [r'\end{axis}', r'\end{tikzpicture}']
    open(f"{out}/twist.tex", 'w').write('\n'.join(lines) + '\n')


def facts(spots):
    """The numbers `neptune.typ` quotes."""
    def span(values, digits=2):
        return f"{min(values):.{digits}f} to {max(values):.{digits}f}"

    xs = np.array(twists['twists_deg'])
    by_day = defaultdict(list)
    for name, curve in twists['curves'].items():
        by_day[frames[name]['time'][:10]].append(np.array(curve))
    # Each day's twist again from its frames drawn at random with replacement, for its spread.
    rng = np.random.default_rng(0)
    for day, curves in sorted(by_day.items()):
        curves = np.array(curves)
        again = [voyager.least(curves[rng.integers(0, len(curves), len(curves))].sum(axis=0), xs) for _ in range(2000)]
        print(f"{day}: twist {twists['days'][day]:.2f} from {len(curves)} frames, bootstrap standard deviation "
              f"{np.std(again):.2f}, 16th to 84th percentile {np.percentile(again, 16):.2f} to {np.percentile(again, 84):.2f}")
    near = 0
    for name, curve in twists['curves'].items():
        near += abs(voyager.least(np.array(curve), xs) - twists['days'][frames[name]['time'][:10]]) <= 1.0
    print(f"frames whose own minimum is within a degree of their day's: {near} of {len(twists['curves'])}")
    rms = [f['limb_rms'] for f in fits.values()]
    print('limb points', span([f['limb_points'] for f in fits.values()], 0), 'rms', span(rms), f"median {np.median(rms):.2f}")
    scales = [f['scale'] for f in fits.values()]
    print('scale', span(scales, 4), f"mean {np.mean(scales):.4f}, standard deviation {np.std(scales):.4f}")
    by_filter = defaultdict(list)
    for name, f in fits.items():
        by_filter[frames[name]['filter']].append(f)
    for flt, fs in sorted(by_filter.items()):
        ks = [f['k'] for f in fs]
        print(f"{flt}: {len(fs)} frames, Minnaert k {np.mean(ks):.3f} +- {np.std(ks):.3f}, B {np.mean([f['albedo'] for f in fs]):.3f}")
    albedo = {flt: float(np.mean([f['albedo'] for name, f in fits.items() if frames[name]['role'] == 'colour' and frames[name]['filter'] == flt]))
              for flt in ('Blue', 'Green', 'Orange')}
    lam, ref = tc.karkoschka(f"{neptune}/data/1993.tab", 'neptune')

    def passband(centre):
        weight = np.exp(-0.5 * ((lam - centre) / 17.0) ** 2)
        return np.sum(ref * weight) / np.sum(weight)

    print(f"blue/green: spectrum {passband(479) / passband(566):.3f}, Voyager {albedo['Blue'] / albedo['Green']:.3f}; "
          f"orange/green: spectrum {passband(591) / passband(566):.3f}, Voyager {albedo['Orange'] / albedo['Green']:.3f}")
    a, lats = luminance['albedo'], luminance['lats']
    relative = a / np.nanmean(a[(lats > WELL_SEEN[0]) & (lats < WELL_SEEN[1])])
    seen = relative[(lats > -70) & (lats < 30)]
    seen = seen[np.isfinite(seen)]
    print(f"brightness from 70 S to 30 N: standard deviation {np.std(seen) * 100:.1f}%, "
          f"2nd to 98th percentile {(np.percentile(seen, 2) - 1) * 100:+.1f}% to {(np.percentile(seen, 98) - 1) * 100:+.1f}%")
    covered = np.mean(np.isfinite(a), axis=1)
    area = np.cos(np.deg2rad(lats))
    print(f"covered all round up to {lats[covered >= 0.99].max():.1f}, partly up to {lats[covered > 0].max():.1f}; "
          f"{np.sum(covered * area) / np.sum(area) * 100:.1f}% of the surface")
    for role in ('luminance', 'colour'):
        chosen = [f for f in frames.values() if f['role'] == role]
        print(role, 'resolution', span([f['resolution_km'] for f in chosen], 0), 'km, times',
              min(f['time'] for f in chosen)[:16], 'to', max(f['time'] for f in chosen)[:16])
    print('phase', span([f['phase'] for f in frames.values()], 1), 'observer latitude',
          span([f['observer_lat'] for f in frames.values()], 1), 'sun latitude', span([f['sun_lat'] for f in frames.values()], 1))
    for name, (lat, lon) in spots.items():
        print(f"{name}: {lat:.1f} N, {lon:.1f} E")


spots = features()
frame_figure()
blemish_figure()
calibration_figure()
maps_figure()
views_figure(spots)
twist_figure()
facts(spots)
