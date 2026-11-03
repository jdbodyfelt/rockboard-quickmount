"""Cut 90 degree countersinks into through holes of an STL.

Counterbores each hole from the minimum-Y face of the mesh (the face at y = 0 in
the reference parts). Hole centres are found from a section across the plate, so
nothing has to be typed in by hand.

Usage:
    python -m tools.stl_countersink SRC.stl DST.stl [--probe 0.7] [--face-dia 6.7]
"""

from __future__ import annotations

import argparse

import manifold3d as mf
import numpy as np
import trimesh


def find_holes(mesh: trimesh.Trimesh, probe_y: float, min_r: float = 1.0) -> list[tuple[float, float, float]]:
    """Return (x, z, bore_radius) for every round hole crossing the probe plane."""
    section = mesh.section(plane_origin=[0.0, probe_y, 0.0], plane_normal=[0, 1, 0])
    if section is None:
        return []
    planar, to_3d = section.to_planar()
    holes = []
    for poly in planar.polygons_full:
        for ring in poly.interiors:
            pts = np.array(ring.coords)[:-1]
            centre = pts.mean(axis=0)
            radius = float(np.linalg.norm(pts - centre, axis=1).mean())
            if radius < min_r:
                continue
            x, _, z, _ = to_3d @ np.array([centre[0], centre[1], 0.0, 1.0])
            holes.append((float(x), float(z), radius))
    return holes


def countersink(
    mesh: trimesh.Trimesh,
    holes: list[tuple[float, float, float]],
    face_dia: float,
    face: str = "min",
    inverted: bool = False,
    over: float = 0.8,
    segments: int = 192,
) -> mf.Manifold:
    """Subtract a 90 degree countersink at each hole.

    `face="min"` or `"max"` picks the y face the countersink opens on. With
    `inverted` the cone is flipped so the hole widens *into* the part: the mouth
    stays at the bore diameter and the recess is buried under the surface.
    """
    solid = mf.Manifold(
        mf.Mesh(
            np.ascontiguousarray(mesh.vertices, np.float32),
            np.ascontiguousarray(mesh.faces, np.uint32),
        )
    )
    top = float(mesh.bounds[1][1])
    face_r = face_dia / 2.0
    depth = face_r - holes[0][2]  # 45 degree flank = 90 degrees included

    for x, z, bore_r in holes:
        if inverted:
            # mouth at the bore, widening to face_dia `depth` into the part
            cutter = mf.Manifold.cylinder(depth + 0.02, bore_r - 0.02, face_r, segments)
        else:
            cutter = mf.Manifold.cylinder(depth + over, face_r + over, bore_r - 0.02, segments)

        if face == "max":
            # mirror about the plate: +Z rotation maps the cut toward +Y
            cutter = cutter.rotate([90.0, 0.0, 0.0])
            y0 = top + over if not inverted else top - depth
        else:
            cutter = cutter.rotate([-90.0, 0.0, 0.0])
            y0 = -over if not inverted else 0.0
        solid = solid - cutter.translate([x, y0, z])
    return solid


def _hole_rings(mesh: trimesh.Trimesh, x: float, z: float, radius: float = 4.0) -> list[tuple[float, float]]:
    """(y, radius) rings on a hole wall, ordered by y."""
    verts = mesh.vertices
    d = np.hypot(verts[:, 0] - x, verts[:, 2] - z)
    sel = verts[d < radius]
    if not len(sel):
        return []
    r = np.hypot(sel[:, 0] - x, sel[:, 2] - z)
    rings = []
    for y in np.unique(np.round(sel[:, 1], 4)):
        rr = r[np.isclose(np.round(sel[:, 1], 4), y)]
        rings.append((float(y), float(rr.max())))
    return sorted(rings)


def _cone(y0: float, r0: float, y1: float, r1: float, x: float, z: float, segments: int) -> mf.Manifold:
    """Solid frustum from (y0, r0) to (y1, r1)."""
    cone = mf.Manifold.cylinder(y1 - y0, r0, r1, segments)
    return cone.rotate([-90.0, 0.0, 0.0]).translate([x, y0, z])


def normalise_countersink(
    mesh: trimesh.Trimesh,
    holes: list[tuple[float, float, float]],
    face_dia: float,
    face: str = "max",
    segments: int = 192,
) -> mf.Manifold:
    """Replace whatever countersink is on `face` with an exact 90 degree one.

    The reference part's countersink measures Ø6.70 at the surface, so cutting a
    Ø6.50 cone into it removes nothing. This adds back the thin wedge between the
    old flare and the specified cone, so the countersink really is `face_dia` at
    the surface, then re-cuts the cone. The through hole is left untouched.
    """
    solid = mf.Manifold(
        mf.Mesh(
            np.ascontiguousarray(mesh.vertices, np.float32),
            np.ascontiguousarray(mesh.faces, np.uint32),
        )
    )
    bore_r = holes[0][2]
    face_r = face_dia / 2.0
    depth = face_r - bore_r

    for x, z, _ in holes:
        rings = _hole_rings(mesh, x, z)
        if len(rings) < 3:
            continue
        if face == "max":
            y_lo = rings[-2][0]
            y_face = rings[-1][0]
            y_start = y_face - depth
            cone_cut = _cone(y_start, bore_r, y_face + 0.6, face_r + 0.6, x, z, segments)
            plug = _cone(y_lo - 0.6, face_r + 0.30, y_face + 0.2, face_r + 0.30, x, z, segments)
            plug = plug - _cone(y_lo - 0.6, bore_r, y_face + 0.2, bore_r, x, z, segments)
            trim = mf.Manifold.cube([10.0, 0.5, 10.0], center=False).translate(
                [x - 5.0, y_face, z - 5.0]
            )
        else:
            y_lo = rings[1][0]
            y_face = rings[0][0]
            y_start = y_face + depth
            cone_cut = _cone(y_face - 0.6, face_r + 0.6, y_start, bore_r, x, z, segments)
            plug = _cone(y_face - 0.2, face_r + 0.30, y_lo + 0.6, face_r + 0.30, x, z, segments)
            plug = plug - _cone(y_face - 0.2, bore_r, y_lo + 0.6, bore_r, x, z, segments)
            trim = mf.Manifold.cube([10.0, 0.5, 10.0], center=False).translate(
                [x - 5.0, y_face - 0.5, z - 5.0]
            )
        solid = (solid + (plug - cone_cut)) - trim
    return solid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("dst")
    parser.add_argument("--probe", type=float, default=0.7, help="y of the section used to find holes")
    parser.add_argument("--face-dia", type=float, default=6.5, help="countersink diameter at the face")
    parser.add_argument("--face", choices=["min", "max"], default="min", help="y face the countersink opens on")
    parser.add_argument(
        "--inverted",
        action="store_true",
        help="keep the mouth at bore size and widen the recess into the part",
    )
    parser.add_argument(
        "--normalise",
        action="store_true",
        help="replace any existing countersink on the chosen face with the specified one",
    )
    args = parser.parse_args()

    mesh = trimesh.load(args.src, force="mesh")
    holes = find_holes(mesh, args.probe)
    if not holes:
        raise SystemExit("no holes found")
    for x, z, r in holes:
        print(f"hole at ({x:7.2f}, {z:7.2f})  bore dia {2 * r:.2f} mm")

    if args.normalise:
        solid = normalise_countersink(mesh, holes, args.face_dia, face=args.face)
    else:
        solid = countersink(mesh, holes, args.face_dia, face=args.face, inverted=args.inverted)
    if solid.status() != mf.Error.NoError:
        raise SystemExit(f"boolean failed: {solid.status()}")

    result = solid.to_mesh()
    out = trimesh.Trimesh(
        vertices=np.asarray(result.vert_properties)[:, :3],
        faces=np.asarray(result.tri_verts),
        process=False,
    )
    trimesh.exchange.export.export_mesh(out, args.dst, file_type="stl")
    print(f"{args.dst}: genus {solid.genus()}, volume {solid.volume():.2f} mm3, {len(out.faces)} triangles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
