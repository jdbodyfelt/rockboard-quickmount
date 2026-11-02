"""Build a whole pedal mount from a component description.

    board attachment  spine(s)   clips strung along an axis + their plate clearance
    pedal attachment  wing(s)    plate/beam surfaces with screw holes,
                                 and/or vertical retainer columns

Usage:
    python -m quickmount.mount --config catalog/pedals/125b_quickmount.yaml
    python -m quickmount.mount --config ... --out out/mount.stl --step
"""

from __future__ import annotations

import argparse
import json
import pathlib

import trimesh
import yaml

from .components import (
    BrandStamp,
    MountHole,
    MountSpec,
    Pocket,
    RetainerColumn,
    SpineSpec,
    WingSpec,
    build_mount,
)
from .keeper import export, load_spec

ROOT = pathlib.Path(__file__).resolve().parent.parent
CODE_VERSION = "0.8.0"


def _points(raw) -> tuple[tuple[float, float], ...]:
    return tuple((float(p[0]), float(p[1])) for p in raw)


def load_mount(path: pathlib.Path) -> MountSpec:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    plate = raw.get("plate", {})

    spines = tuple(
        SpineSpec(
            clips=int(s.get("clips", 2)),
            post_spacing=float(s["post_spacing_mm"]),
            axis=s.get("axis", "x"),
            clip_width=float(s["clip_width_mm"]),
            arch_scale=float(s.get("arch_scale", 1.0)),
            clearance=float(s.get("clearance_mm", 2.0)),
            clearance_width=float(s.get("clearance_width_mm", 0.0)),
            clearance_radius=float(s.get("clearance_radius_mm", 0.0)),
            flare=s.get("flare", "outward"),
            offset=float(s.get("offset_mm", 0.0)),
            name=s.get("name", "spine"),
        )
        for s in raw.get("spines", [])
    )

    def _holes(items) -> tuple[MountHole, ...]:
        return tuple(
            MountHole(
                x=float(h["x"]),
                y=float(h["y"]),
                bore=float(h.get("bore_mm", 3.7)),
                csk_dia=float(h.get("csk_dia_mm", 6.7)),
                csk_face=h.get("csk_face", "bottom"),
            )
            for h in items or ()
        )

    def _columns(items) -> tuple[RetainerColumn, ...]:
        return tuple(
            RetainerColumn(
                x=float(c["x"]),
                y=float(c["y"]),
                height=float(c.get("height_mm", 10.0)),
                thickness=float(c.get("thickness_mm", 2.5)),
                depth=float(c.get("depth_mm", 12.0)),
                facing=c.get("facing", "-x"),
                lip=float(c.get("lip_mm", 1.2)),
                name=c.get("name", "column"),
            )
            for c in items or ()
        )

    wings = tuple(
        WingSpec(
            name=w.get("name", "wing"),
            outline=_points(w["outline_mm"]) if w.get("outline_mm") else (),
            width_mm=float(w.get("width_mm", 0.0)),
            depth_mm=float(w.get("depth_mm", 0.0)),
            corner_radius=float(w.get("corner_radius_mm", 0.0)),
            cx=float(w.get("cx", 0.0)),
            cy=float(w.get("cy", 0.0)),
            holes=_holes(w.get("holes")),
            columns=_columns(w.get("columns")),
            pockets=tuple(
                Pocket(
                    cx=float(p.get("cx", 0.0)),
                    cy=float(p.get("cy", 0.0)),
                    width=float(p["width_mm"]),
                    depth=float(p["depth_mm"]),
                    corner_radius=float(p.get("corner_radius_mm", 0.0)),
                    through=bool(p.get("through", True)),
                    depth_mm=float(p.get("pocket_depth_mm", 0.0)),
                    name=p.get("name", "pocket"),
                )
                for p in w.get("pockets", [])
            ),
        )
        for w in raw.get("wings", [])
    )

    return MountSpec(
        name=raw.get("id", path.stem),
        thickness=float(plate.get("thickness_mm", 3.0)),
        spines=spines,
        wings=wings,
        holes=_holes(raw.get("mount_holes")),
        columns=_columns(raw.get("columns")),
        brand_stamp=(
            BrandStamp(
                model_number=str(stamp["model_number"]),
                x=float(stamp.get("cx", 0.0)),
                y=float(stamp.get("cy", 0.0)),
                font=stamp.get("font", "Arial"),
                font_path=(
                    str((path.parent / stamp["font_path"]).resolve())
                    if stamp.get("font_path")
                    else None
                ),
                font_size=float(stamp.get("font_size_mm", 5.0)),
                bold_amount=float(stamp.get("bold_amount_mm", 0.0)),
                line_spacing=float(stamp.get("line_spacing_mm", 6.0)),
                model_gap=float(stamp.get("model_gap_mm", 10.0)),
                depth=float(stamp.get("depth_mm", 0.4)),
                frame_padding=float(stamp.get("frame_padding_mm", 1.2)),
                frame_width=float(stamp.get("frame_width_mm", 0.8)),
                frame_radius=float(stamp.get("frame_radius_mm", 2.0)),
                rotation=float(stamp.get("rotation_deg", 90.0)),
            )
            if (stamp := raw.get("brand_stamp"))
            else None
        ),
    )


def report(mesh: trimesh.Trimesh) -> dict:
    return {
        "triangles": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "volume_mm3": round(float(mesh.volume), 1),
        "extents_mm": [round(float(v), 2) for v in mesh.extents],
    }


def measure_holes(mesh: trimesh.Trimesh, holes: tuple[MountHole, ...], thickness: float) -> list[dict]:
    """Check each hole's bore and countersink against the spec, from the mesh."""
    found = []
    for hole in holes:
        entry = {"at": [hole.x, hole.y], "spec_bore": hole.bore, "spec_csk": hole.csk_dia}
        face_offset = min(0.001, thickness / 2.0)
        for label, z in (("bottom", face_offset), ("top", thickness - face_offset)):
            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if section is None:
                continue
            planar, to_3d = section.to_2D()
            for poly in planar.polygons_full:
                for ring in poly.interiors:
                    pts = _rm_dup(ring)
                    centre = pts.mean(axis=0)
                    r = float((((pts - centre) ** 2).sum(axis=1) ** 0.5).mean())
                    px, py, _, _ = to_3d @ [centre[0], centre[1], 0.0, 1.0]
                    if abs(px - hole.x) < 1.0 and abs(py - hole.y) < 1.0:
                        entry[f"{label}_dia"] = round(2 * r, 2)
        found.append(entry)
    return found


def _rm_dup(ring):
    import numpy as np

    pts = np.array(ring.coords)
    return pts[:-1] if len(pts) > 1 else pts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--step", action="store_true")
    args = parser.parse_args()

    config = pathlib.Path(args.config)
    raw = yaml.safe_load(config.read_text(encoding="utf-8"))
    mount = load_mount(config)
    clip_path = raw.get("clip")
    spec = load_spec(ROOT / clip_path) if clip_path else load_spec()
    part = build_mount(mount, spec)

    out = pathlib.Path(args.out) if args.out else ROOT / "out" / f"{mount.name}.stl"
    out.parent.mkdir(parents=True, exist_ok=True)
    step = out.with_suffix(".step") if args.step else None
    export(part, str(out), str(step) if step else None)

    mesh = trimesh.load(str(out), force="mesh")
    rep = report(mesh)
    holes = list(mount.holes)
    for wing in mount.wings:
        holes.extend(wing.holes)

    manifest = {
        "code_version": CODE_VERSION,
        "config": str(config),
        "part": mount.name,
        "thickness_mm": mount.thickness,
        "spines": [
            {
                "name": s.name,
                "clips": s.clips,
                "axis": s.axis,
                "post_spacing_mm": s.post_spacing,
                "clip_width_mm": s.clip_width,
                "flare": s.flare,
            }
            for s in mount.spines
        ],
        "wings": [{"name": w.name, "holes": len(w.holes), "columns": len(w.columns)} for w in mount.wings],
        "brand_stamp": (
            {
                "lines": ["Melting", "Skies", mount.brand_stamp.model_number],
                "face": "pedal",
                "center_mm": [mount.brand_stamp.x, mount.brand_stamp.y],
                "font": mount.brand_stamp.font,
                "font_size_mm": mount.brand_stamp.font_size,
                "bold_amount_mm": mount.brand_stamp.bold_amount,
                "line_spacing_mm": mount.brand_stamp.line_spacing,
                "model_gap_mm": mount.brand_stamp.model_gap,
                "depth_mm": mount.brand_stamp.depth,
                "remaining_plate_mm": round(mount.thickness - mount.brand_stamp.depth, 2),
                "frame_padding_mm": mount.brand_stamp.frame_padding,
                "frame_width_mm": mount.brand_stamp.frame_width,
                "frame_radius_mm": mount.brand_stamp.frame_radius,
                "rotation_deg": mount.brand_stamp.rotation,
            }
            if mount.brand_stamp is not None
            else None
        ),
        "mesh": rep,
        "holes": measure_holes(mesh, tuple(holes), mount.thickness),
    }

    print(f"[{'ok' if rep['watertight'] else 'FAIL'}] {mount.name}")
    print(f"   size     {rep['extents_mm']}  volume {rep['volume_mm3']} mm3  {rep['triangles']} tris")
    for spine in manifest["spines"]:
        print(f"   spine    {spine['clips']} clips, {spine['axis']} axis, "
              f"posts {spine['post_spacing_mm']:.2f} mm apart, {spine['flare']}")
    for hole in manifest["holes"]:
        print(f"   hole     ({hole['at'][0]:7.2f}, {hole['at'][1]:7.2f})  "
              f"pedal face {hole.get('bottom_dia', '?')}  board face {hole.get('top_dia', '?')}")

    sidecar = out.with_suffix(".json")
    sidecar.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest -> {sidecar}")
    return 0 if rep["watertight"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
