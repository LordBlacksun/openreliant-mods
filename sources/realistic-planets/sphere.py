"""Writes a sphere for a planet as a Wavefront OBJ file, for `sltool shp from-obj`.

The sphere has its poles on Y, as the game turns planets about their own Y, and it carries an
equirectangular map: the picture's top is the north pole, its middle column faces +Z, the model's
front, and east runs toward +X, so that a map drawn as seen from outside looks right on the planet.

With `--polar`, it is an oblate spheroid, flattened along Y, such as Jupiter. Its parallels, the rows
of vertices, stand at planetocentric latitudes, as Cassini's maps of Jupiter have them; on a sphere
both latitudes agree.

With `--ring`, a flat ring follows in the plane of the equator, such as Saturn's: a layer facing
north and one facing south, each with a vertex at the inner and the outer radius for every segment,
so that the normals the engine works out stay flat. Its texture's width runs from the inner radius
to the outer, and every row of it is alike.

Each vertex is written once, the seam's and the poles' included, and the texture coordinates go
with each corner. The game works out a planet's normals again from its faces, so a shared vertex
keeps the lighting smooth across the seam, where a split one would show a line.

    python3 sphere.py neptune.obj --radius 1280625 --texture realistic_planets_neptune
    python3 sphere.py jupiter.obj --radius 1280625 --polar 1197549 --texture realistic_planets_jupiter
    python3 sphere.py saturn.obj --radius 2044626 --polar 1844330 --texture realistic_planets_saturn \
        --ring 2510492 4783505 --ring-texture realistic_planets_saturn_rings
"""

import argparse
import math


def write(out, name: str, texture: str, radius: float, polar: float, columns: int, rows: int) -> tuple[int, int]:
    """Writes the sphere, and returns how many vertices and texture coordinates it has."""
    parallels = range(1, rows)
    # Vertices: the north pole, each parallel from north to south, then the south pole.
    north = 1
    def vertex(parallel: int, column: int) -> int:
        return 2 + (parallel - 1) * columns + column % columns
    south = 2 + (rows - 1) * columns
    out.write(f"# A sphere of radius {radius:g}, polar radius {polar:g}, {columns} columns by {rows} rows, by sphere.py\n")
    out.write(f"o {name}\n")
    # Each point's direction from the middle, at planetocentric latitudes.
    directions = [(0.0, 1.0, 0.0)]
    for parallel in parallels:
        latitude = math.pi / 2 - math.pi * parallel / rows
        for column in range(columns):
            longitude = 2 * math.pi * column / columns - math.pi
            directions.append((math.cos(latitude) * math.sin(longitude), math.sin(latitude), math.cos(latitude) * math.cos(longitude)))
    directions.append((0.0, -1.0, 0.0))
    points, normals = [], []
    for x, y, z in directions:
        # Out along the direction to the spheroid, and its normal there.
        r = radius * polar / math.hypot(polar * math.hypot(x, z), radius * y)
        points.append((x * r, y * r, z * r))
        nx, ny, nz = x * r / radius ** 2, y * r / polar ** 2, z * r / radius ** 2
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        normals.append((nx / length, ny / length, nz / length))
    for x, y, z in points:
        out.write(f"v {x:.3f} {y:.3f} {z:.3f}\n")
    for x, y, z in normals:
        out.write(f"vn {x:.6f} {y:.6f} {z:.6f}\n")

    # Texture coordinates: each parallel's columns with the seam's twice, at 0 and 1, then a point at
    # each pole for every column, in the middle of the column.
    def coordinate(parallel: int, column: int) -> int:
        return 1 + (parallel - 1) * (columns + 1) + column
    for parallel in parallels:
        for column in range(columns + 1):
            out.write(f"vt {column / columns:.6f} {1 - parallel / rows:.6f}\n")
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
    for parallel in range(1, rows - 1):
        for column in range(columns):
            a = corner(vertex(parallel, column), coordinate(parallel, column))
            b = corner(vertex(parallel + 1, column), coordinate(parallel + 1, column))
            c = corner(vertex(parallel + 1, column + 1), coordinate(parallel + 1, column + 1))
            d = corner(vertex(parallel, column + 1), coordinate(parallel, column + 1))
            out.write(f"f {a} {b} {c}\nf {a} {c} {d}\n")
    for column in range(columns):
        bottom = pole_coordinates + columns + column
        b = corner(vertex(rows - 1, column), coordinate(rows - 1, column))
        c = corner(vertex(rows - 1, column + 1), coordinate(rows - 1, column + 1))
        out.write(f"f {b} {corner(south, bottom)} {c}\n")
    return len(points), pole_coordinates - 1 + 2 * columns


def write_ring(out, texture: str, inner: float, outer: float, segments: int, vertices: int, coordinates: int) -> None:
    """Writes a flat ring in the plane of the equator after `vertices` vertices and `coordinates`
    texture coordinates: the layer facing north, then the one facing south, each counter-clockwise
    seen from the side it faces."""
    out.write(f"# A ring from radius {inner:g} to {outer:g}, {segments} segments, by sphere.py\n")
    for _ in range(2):
        for segment in range(segments):
            angle = 2 * math.pi * segment / segments - math.pi
            for radius in (inner, outer):
                out.write(f"v {radius * math.sin(angle):.3f} 0 {radius * math.cos(angle):.3f}\n")
    for up in (1, -1):
        out.write(f"vn 0 {up} 0\n" * (2 * segments))
    out.write("vt 0 0.5\nvt 1 0.5\n")
    inside, outside = coordinates + 1, coordinates + 2
    out.write(f"usemtl {texture}\n")
    for layer in range(2):
        def corner(segment: int, edge: int) -> str:
            v = vertices + 2 * segments * layer + 2 * (segment % segments) + edge + 1
            return f"{v}/{(inside, outside)[edge]}/{v}"
        for segment in range(segments):
            a, b, c, d = corner(segment, 0), corner(segment, 1), corner(segment + 1, 1), corner(segment + 1, 0)
            out.write(f"f {a} {b} {c}\nf {a} {c} {d}\n" if layer == 0 else f"f {a} {c} {b}\nf {a} {d} {c}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a planet's sphere as an OBJ file.")
    parser.add_argument("out", help="the OBJ file to write")
    parser.add_argument("--radius", type=float, required=True, help="the radius, in the game's units")
    parser.add_argument("--polar", type=float, help="the polar radius, for an oblate planet; the radius by default")
    parser.add_argument("--texture", required=True, help="the texture's name, without its extension")
    parser.add_argument("--name", default="planet", help="the part's name")
    parser.add_argument("--columns", type=int, default=128, help="segments round the equator")
    parser.add_argument("--rows", type=int, default=64, help="segments from pole to pole")
    parser.add_argument("--ring", type=float, nargs=2, metavar=("INNER", "OUTER"), help="a ring's inner and outer radius")
    parser.add_argument("--ring-texture", help="the ring texture's name, without its extension")
    parser.add_argument("--ring-segments", type=int, default=512, help="the ring's segments round the planet")
    args = parser.parse_args()
    if args.ring and not args.ring_texture:
        parser.error("--ring needs --ring-texture")
    with open(args.out, "w") as out:
        vertices, coordinates = write(out, args.name, args.texture, args.radius, args.polar or args.radius, args.columns, args.rows)
        if args.ring:
            write_ring(out, args.ring_texture, *args.ring, args.ring_segments, vertices, coordinates)


if __name__ == "__main__":
    main()
