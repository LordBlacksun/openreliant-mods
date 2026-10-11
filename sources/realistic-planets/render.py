"""Draws a planet from its equirectangular texture, as seen from far away, for the mod's thumbnail and
the figures of its notes: an orthographic view from a latitude and longitude, lit from a direction
by a light of a colour, with Minnaert's limb darkening, on black. Nothing of the game's goes into it.

    python3 render.py texture.png out.png --size 512 --lat -25 --lon 0 --sun-lat -20 --sun-lon 20 --k 0.75

`--light 1 1 0.8` lights the planet as StarLancer does, apart from the game's tone curve.
"""
import argparse
import subprocess

import numpy as np


def load(path):
    w, h = map(int, subprocess.run(['magick', 'identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split())
    raw = subprocess.run(['magick', path, '-colorspace', 'RGB', '-depth', '16', 'rgb:-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='<u2').reshape(h, w, 3).astype(np.float64) / 65535.0


def unit(lat, lon):
    la, lo = np.deg2rad(lat), np.deg2rad(lon)
    return np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def render(tex, size, lat, lon, sun_lat, sun_lon, k, light=(1.0, 1.0, 1.0)):
    view = unit(lat, lon)                       # from the planet's centre toward the viewer
    north = np.array([0.0, 0.0, 1.0]) - view[2] * view
    north /= np.linalg.norm(north)
    east = np.cross(north, view)                # to the right on the screen, as seen from outside
    sun = unit(sun_lat, sun_lon)
    ys, xs = np.mgrid[0:size, 0:size].astype(float)
    u = (xs + 0.5) / size * 2 - 1
    v = 1 - (ys + 0.5) / size * 2
    r2 = u * u + v * v
    disk = r2 < 1
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    p = u[..., None] * east + v[..., None] * north + z[..., None] * view
    plat = np.degrees(np.arcsin(np.clip(p[..., 2], -1, 1)))
    plon = np.degrees(np.arctan2(p[..., 1], p[..., 0]))
    h, w = tex.shape[:2]
    col = ((plon + 180) / 360 * w).astype(int) % w
    row = np.clip(((90 - plat) / 180 * h).astype(int), 0, h - 1)
    albedo = tex[row, col]
    mu, mu0 = z, np.clip(p @ sun, 0, 1)
    shade = np.where(mu0 > 0, mu0 ** k * np.clip(mu, 1e-3, 1) ** (k - 1), 0)
    out = np.where(disk[..., None], albedo * shade[..., None] * np.asarray(light), 0)
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
    p.add_argument('--size', type=int, default=512)
    p.add_argument('--lat', type=float, default=-25); p.add_argument('--lon', type=float, default=0)
    p.add_argument('--sun-lat', type=float, default=-20); p.add_argument('--sun-lon', type=float, default=20)
    p.add_argument('--k', type=float, default=0.75, help="Minnaert's exponent")
    p.add_argument('--light', type=float, nargs=3, default=(1.0, 1.0, 1.0), metavar=('R', 'G', 'B'), help="the light's colour")
    a = p.parse_args()
    save(render(load(a.texture), a.size, a.lat, a.lon, a.sun_lat, a.sun_lon, a.k, a.light), a.out)


if __name__ == '__main__':
    main()
