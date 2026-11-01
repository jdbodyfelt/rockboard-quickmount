"""ASCII cross-section viewer for STL meshes, in world coordinates.

Usage: python tools/stl_section.py <file.stl> <axis> <values> [nu] [nv]
  axis:   x, y or z -- the slice plane is normal to this axis
  values: comma separated slice positions in mm
The two plotted axes are the remaining world axes, labelled on output.
"""
import sys

import numpy as np
import trimesh
from shapely.geometry import Point
from shapely.geometry import Polygon as SPoly
from shapely.ops import unary_union

AXES = {
    "x": ([1.0, 0.0, 0.0], 1, 2, "Y", "Z"),
    "y": ([0.0, 1.0, 0.0], 0, 2, "X", "Z"),
    "z": ([0.0, 0.0, 1.0], 0, 1, "X", "Y"),
}


def world_shape(mesh, axis, value):
    normal, iu, iv, _, _ = AXES[axis]
    origin = [0.0, 0.0, 0.0]
    origin["xyz".index(axis)] = value
    sec = mesh.section(plane_origin=origin, plane_normal=normal)
    if sec is None:
        return None
    planar, transform = sec.to_2D()
    polys = []
    for poly in planar.polygons_full:
        for ring in [poly.exterior, *poly.interiors]:
            pts = np.asarray(ring.coords)
            if len(pts) < 4:
                continue
            pts3 = trimesh.transform_points(np.column_stack([pts, np.zeros(len(pts))]), transform)
            polys.append(SPoly(pts3[:, [iu, iv]]))
    if not polys:
        return None
    return unary_union(polys)


def render(mesh, axis, value, nu=64, nv=26):
    shape = world_shape(mesh, axis, value)
    _, _, _, uname, vname = AXES[axis]
    if shape is None or shape.is_empty:
        print(f"  {axis}={value:g} empty")
        return
    minx, miny, maxx, maxy = shape.bounds
    su = (maxx - minx) / nu
    sv = (maxy - miny) / nv
    print(f"  {axis}={value:g}   {uname} [{minx:.2f} .. {maxx:.2f}]   {vname} [{miny:.2f} .. {maxy:.2f}]")
    print("   " + "".join(str(int(abs(minx + (i + 0.5) * su)) % 10) for i in range(nu)))
    for j in range(nv):
        v = maxy - (j + 0.5) * sv
        row = "".join("#" if shape.contains(Point(minx + (i + 0.5) * su, v)) else "." for i in range(nu))
        print(f"{v:8.2f}|{row}|")


def main():
    path = sys.argv[1]
    mesh = trimesh.load(path, force="mesh")
    print(f"{path}\n  bounds {np.round(mesh.bounds, 2).tolist()}  extents {np.round(mesh.extents, 2).tolist()}")
    axis = sys.argv[2]
    values = [float(v) for v in sys.argv[3].split(",")]
    nu = int(sys.argv[4]) if len(sys.argv) > 4 else 64
    nv = int(sys.argv[5]) if len(sys.argv) > 5 else 26
    for value in values:
        render(mesh, axis, value, nu, nv)


if __name__ == "__main__":
    main()
