"""Print world-coordinate cross-section polygon vertices for an STL.

Usage: python tools/stl_profile.py <file.stl> <axis> <value> [tolerance]
  axis: x, y or z (slice plane normal)
  value: slice position in mm
  tolerance: shapely simplify tolerance (default 0.05 mm)
Vertices are printed as (u, v) where u/v are the two in-plane world axes:
  x-slice -> (Y, Z)   y-slice -> (X, Z)   z-slice -> (X, Y)
"""
import sys

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

AXES = {
    "x": ([1.0, 0.0, 0.0], "Y", "Z", 1, 2),
    "y": ([0.0, 1.0, 0.0], "X", "Z", 0, 2),
    "z": ([0.0, 0.0, 1.0], "X", "Y", 0, 1),
}


def world_polygons(mesh, axis, value):
    normal, _, _, iu, iv = AXES[axis]
    origin = [0.0, 0.0, 0.0]
    origin["xyz".index(axis)] = value
    sec = mesh.section(plane_origin=origin, plane_normal=normal)
    if sec is None:
        return []
    planar, transform = sec.to_2D()
    out = []
    for poly in planar.polygons_full:
        rings = [np.asarray(poly.exterior.coords)]
        rings += [np.asarray(r.coords) for r in poly.interiors]
        world_rings = []
        for ring in rings:
            pts3 = trimesh.transform_points(np.column_stack([ring, np.zeros(len(ring))]), transform)
            world_rings.append(np.column_stack([pts3[:, iu], pts3[:, iv]]))
        out.append(world_rings)
    return out


def main():
    path, axis, value = sys.argv[1], sys.argv[2], float(sys.argv[3])
    tol = float(sys.argv[4]) if len(sys.argv) > 4 else 0.05
    mesh = trimesh.load(path, force="mesh")
    _, uname, vname, _, _ = AXES[axis]
    print(f"{path}\n{axis}={value:g}  plotting ({uname}, {vname})")
    for idx, rings in enumerate(world_polygons(mesh, axis, value)):
        print(f"\n-- polygon {idx} --")
        for ridx, ring in enumerate(rings):
            pts = Polygon(ring).simplify(tol)
            coords = np.asarray(pts.exterior.coords)
            label = "exterior" if ridx == 0 else f"hole{ridx}"
            print(f"   {label}: {len(coords) - 1} pts")
            for u, v in coords[:-1]:
                print(f"     {u:8.2f} {v:8.2f}")


if __name__ == "__main__":
    main()
