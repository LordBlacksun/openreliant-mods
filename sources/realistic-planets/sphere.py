"""Writes a sphere for a planet as a Wavefront OBJ file, for `sltool shp from-obj`.

The sphere has its poles on Y, as the game turns planets about their own Y, and it carries an
equirectangular map: the picture's top is the north pole, its middle column faces +Z, the model's
front, and east runs toward +X, so that a map drawn as seen from outside looks right on the planet.

Each vertex is written once, the seam's and the poles' included, and the texture coordinates go
with each corner. The game works out a planet's normals again from its faces, so a shared vertex
keeps the lighting smooth across the seam, where a split one would show a line.

    python3 sphere.py neptune.obj --radius 1280625 --texture realistic_planets_neptune
"""

import argparse
import math


def write(out, name: str, texture: str, radius: float, columns: int, rows: int) -> None:
    rings = range(1, rows)
    # Vertices: the north pole, each ring from north to south, then the south pole.
    north = 1
    def vertex(ring: int, column: int) -> int:
        return 2 + (ring - 1) * columns + column % columns
    south = 2 + (rows - 1) * columns
    out.write(f"# A sphere of radius {radius:g}, {columns} columns by {rows} rows, by sphere.py\n")
    out.write(f"o {name}\n")
    points = [(0.0, 1.0, 0.0)]
    for ring in rings:
        latitude = math.pi / 2 - math.pi * ring / rows
        for column in range(columns):
            longitude = 2 * math.pi * column / columns - math.pi
            points.append((math.cos(latitude) * math.sin(longitude), math.sin(latitude), math.cos(latitude) * math.cos(longitude)))
    points.append((0.0, -1.0, 0.0))
    for x, y, z in points:
        out.write(f"v {x * radius:.3f} {y * radius:.3f} {z * radius:.3f}\n")
    for x, y, z in points:
        out.write(f"vn {x:.6f} {y:.6f} {z:.6f}\n")

    # Texture coordinates: each ring's columns with the seam's twice, at 0 and 1, then a point at
    # each pole for every column, in the middle of the column.
    def coordinate(ring: int, column: int) -> int:
        return 1 + (ring - 1) * (columns + 1) + column
    for ring in rings:
        for column in range(columns + 1):
            out.write(f"vt {column / columns:.6f} {1 - ring / rows:.6f}\n")
    pole_coordinates = (rows - 1) * (columns + 1) + 1
    for column in range(columns):
        out.write(f"vt {(column + 0.5) / columns:.6f} 1\n")
    for column in range(columns):
        out.write(f"vt {(column + 0.5) / columns:.6f} 0\n")

    # Faces, counter-clockwise seen from outside.
    out.write(f"usemtl {texture}\n")
    def corner(v: int, t: int) -> str:
        return f"{v}/{t}/{v}"
    for column in range(columns):
        top = pole_coordinates + column
        out.write(f"f {corner(north, top)} {corner(vertex(1, column), coordinate(1, column))} {corner(vertex(1, column + 1), coordinate(1, column + 1))}\n")
    for ring in range(1, rows - 1):
        for column in range(columns):
            a = corner(vertex(ring, column), coordinate(ring, column))
            b = corner(vertex(ring + 1, column), coordinate(ring + 1, column))
            c = corner(vertex(ring + 1, column + 1), coordinate(ring + 1, column + 1))
            d = corner(vertex(ring, column + 1), coordinate(ring, column + 1))
            out.write(f"f {a} {b} {c}\nf {a} {c} {d}\n")
    for column in range(columns):
        bottom = pole_coordinates + columns + column
        b = corner(vertex(rows - 1, column), coordinate(rows - 1, column))
        c = corner(vertex(rows - 1, column + 1), coordinate(rows - 1, column + 1))
        out.write(f"f {b} {corner(south, bottom)} {c}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a planet's sphere as an OBJ file.")
    parser.add_argument("out", help="the OBJ file to write")
    parser.add_argument("--radius", type=float, required=True, help="the radius, in the game's units")
    parser.add_argument("--texture", required=True, help="the texture's name, without its extension")
    parser.add_argument("--name", default="planet", help="the part's name")
    parser.add_argument("--columns", type=int, default=128, help="segments round the equator")
    parser.add_argument("--rows", type=int, default=64, help="segments from pole to pole")
    args = parser.parse_args()
    with open(args.out, "w") as out:
        write(out, args.name, args.texture, args.radius, args.columns, args.rows)


if __name__ == "__main__":
    main()
