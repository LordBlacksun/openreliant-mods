"""Draws a planet from its equirectangular texture, as seen from far away, for the mod's thumbnail and
the figures of its notes: an orthographic view from a latitude and longitude, lit from a direction
by a light of a colour, with Minnaert's limb darkening, on black. Nothing of the game's goes into it.
`--polar` flattens the planet, its polar radius that share of its equator's; the texture's latitudes
are then planetocentric, as `sphere.py`'s spheres take them.

    python3 render.py texture.png out.png --size 512 --lat -25 --lon 0 --sun-lat -20 --sun-lon 20 --k 0.75

`--k` takes one exponent, or one each for red, green and blue, as the mod's surface functions do, and
`--least` holds the limb's factor at its value at that cosine of the view, as they do too.
`--light 1 1 0.8` lights the planet as StarLancer does, apart from the game's tone curve.

`--ring` adds a ring in the plane of the equator, from its strip of a texture, as `sphere.py` writes it,
between an inner and an outer radius, in the equator's radii. It's drawn as the mod's surface
function `rings.glsl` draws it, lit as if the sun stood at `--ring-sun`, the cosine of its angle from
the ring's pole, but blended in linear light. The planet hides the ring behind it, and neither
shadows the other. `--extent` is how many of the equator's radii the picture reaches above and below
the middle, and `--aspect` its width over its height.
"""
import argparse
import subprocess

import numpy as np


def load(path, alpha=False):
    """A picture as linear RGB from 0 to 1, with its alpha as it's stored if `alpha` is set."""
    w, h = map(int, subprocess.run(['magick', 'identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split())
    channels = 'rgba' if alpha else 'rgb'
    raw = subprocess.run(['magick', path, '-colorspace', 'RGB', '-depth', '16', f'{channels}:-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='<u2').reshape(h, w, len(channels)).astype(np.float64) / 65535.0


def unit(lat, lon):
    la, lo = np.deg2rad(lat), np.deg2rad(lon)
    return np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def render(tex, size, lat, lon, sun_lat, sun_lon, k, light=(1.0, 1.0, 1.0), polar=1.0, ring=None, extent=1.0, aspect=1.0, least=0.0):
    """The picture, `size` pixels high. `k` is Minnaert's exponent, or one for each channel. `ring`
    is the ring's texture, its inner and outer radius, and the cosine of the sun's angle from its
    pole that it's lit for, or None. Nearer the limb than `least`, the cosine of the view, the limb's
    factor stays as it is there."""
    view = unit(lat, lon)                       # from the planet's centre toward the viewer
    north = np.array([0.0, 0.0, 1.0]) - view[2] * view
    north /= np.linalg.norm(north)
    east = np.cross(north, view)                # to the right on the screen, as seen from outside
    sun = unit(sun_lat, sun_lon)
    width = int(round(size * aspect))
    ys, xs = np.mgrid[0:size, 0:width].astype(float)
    u = ((xs + 0.5) / width * 2 - 1) * extent * aspect
    v = (1 - (ys + 0.5) / size * 2) * extent
    plane = u[..., None] * east + v[..., None] * north
    # Where each pixel's ray toward the planet meets it: squeezed along the axis, the spheroid is a
    # unit sphere, and the nearer root of the ray's quadratic is the side that faces the viewer.
    squeeze = np.array([1.0, 1.0, 1.0 / polar])
    o = plane * squeeze
    d = view * squeeze
    a, b, c = d @ d, o @ d, np.sum(o * o, axis=-1) - 1
    disc = b * b - a * c
    disk = disc > 0
    t = (-b + np.sqrt(np.clip(disc, 0, None))) / a
    p = plane + t[..., None] * view
    normal = p * squeeze ** 2
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    plat = np.degrees(np.arcsin(np.clip(p[..., 2] / np.linalg.norm(p, axis=-1), -1, 1)))
    plon = np.degrees(np.arctan2(p[..., 1], p[..., 0]))
    h, w = tex.shape[:2]
    col = ((plon + 180) / 360 * w).astype(int) % w
    row = np.clip(((90 - plat) / 180 * h).astype(int), 0, h - 1)
    albedo = tex[row, col]
    mu, mu0 = np.clip(normal @ view, 0, 1), np.clip(normal @ sun, 0, 1)
    k = np.broadcast_to(np.asarray(k, dtype=float), (3,))
    shade = np.where(mu0[..., None] > 0, mu0[..., None] ** k * np.clip(mu, max(least, 1e-3), 1)[..., None] ** (k - 1), 0)
    out = np.where(disk[..., None], albedo * shade * np.asarray(light), 0)
    if ring is not None and abs(view[2]) > 1e-6:
        strip, inner, outer, ring_sun = ring
        # Where each ray crosses the plane of the equator, and whether that's in front of the planet.
        crossing = -plane[..., 2] / view[2]
        radius = np.linalg.norm(plane + crossing[..., None] * view, axis=-1)
        on_ring = (radius >= inner) & (radius <= outer) & (~disk | (crossing > t))
        texel = np.clip(((radius - inner) / (outer - inner) * strip.shape[1]).astype(int), 0, strip.shape[1] - 1)
        sample = strip[strip.shape[0] // 2, texel]
        clear = 1 - sample[..., 3]
        slant = abs(view[2])
        scattered = sample[..., :3] * (ring_sun / (slant + ring_sun) * (1 - clear ** (1 / slant + 1 / ring_sun)))[..., None]
        out = np.where(on_ring[..., None], scattered + (clear ** (1 / slant))[..., None] * out, out)
    return np.clip(out, 0, 1)


def save(img, path):
    """Writes a picture of linear RGB from 0 to 1 as an 8-bit sRGB PNG."""
    h, w = img.shape[:2]
    data = (np.clip(img, 0, 1) * 65535).astype('<u2').tobytes()
    subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '16', '-endian', 'LSB', 'rgb:-', '-set', 'colorspace', 'RGB',
                    '-colorspace', 'sRGB', '-depth', '8', path], input=data, check=True)


def main():
    p = argparse.ArgumentParser(description="Draw a planet from its texture.")
    p.add_argument('texture'); p.add_argument('out')
    p.add_argument('--size', type=int, default=512, help="the picture's height in pixels")
    p.add_argument('--lat', type=float, default=-25); p.add_argument('--lon', type=float, default=0)
    p.add_argument('--sun-lat', type=float, default=-20); p.add_argument('--sun-lon', type=float, default=20)
    p.add_argument('--k', type=float, nargs='+', default=[0.75], help="Minnaert's exponent, or one for each of red, green and blue")
    p.add_argument('--least', type=float, default=0.0, help="the cosine of the view nearer the limb than which the limb's factor holds")
    p.add_argument('--light', type=float, nargs=3, default=(1.0, 1.0, 1.0), metavar=('R', 'G', 'B'), help="the light's colour")
    p.add_argument('--polar', type=float, default=1.0, help="the polar radius over the equator's")
    p.add_argument('--ring', nargs=3, metavar=('TEXTURE', 'INNER', 'OUTER'), help="a ring's texture, and its radii in the equator's")
    p.add_argument('--ring-sun', type=float, default=0.5, help="the cosine of the sun's angle from the ring's pole it's lit for")
    p.add_argument('--extent', type=float, default=1.0, help="the equator's radii the picture reaches above and below the middle")
    p.add_argument('--aspect', type=float, default=1.0, help="the picture's width over its height")
    a = p.parse_args()
    ring = (load(a.ring[0], alpha=True), float(a.ring[1]), float(a.ring[2]), a.ring_sun) if a.ring else None
    k = a.k[0] if len(a.k) == 1 else a.k
    save(render(load(a.texture), a.size, a.lat, a.lon, a.sun_lat, a.sun_lon, k, a.light, a.polar, ring, a.extent, a.aspect, a.least), a.out)


if __name__ == '__main__':
    main()
