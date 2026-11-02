"""Build keeper rings and arrangements.

Emits the C-shaped keeper ring and bar arrangements of them, at the board pitch.
No pedal-specific plates: this is the mechanism only.

Usage: python -m quickmount.build [--out out] [--step] [--rings 1,2,3]
"""

from __future__ import annotations

import argparse
import json
import pathlib

import trimesh
import yaml

from .keeper import build_arrangement, build_ring, export, load_spec

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
CODE_VERSION = "0.4.0"
OUTPUT_DIRECTORY = "Keeper"


def load_board(name: str) -> dict:
    return yaml.safe_load((CATALOG / "boards" / f"{name}.yaml").read_text(encoding="utf-8"))


def report(mesh: trimesh.Trimesh) -> dict:
    return {
        "triangles": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "volume_mm3": round(float(mesh.volume), 1),
        "extents_mm": [round(float(v), 2) for v in mesh.extents],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "out"))
    ap.add_argument("--board", default="cinque_5_2")
    ap.add_argument("--step", action="store_true")
    ap.add_argument("--rings", default="1,2,3")
    ap.add_argument(
        "--ring-width",
        type=float,
        default=None,
        help="across-slot width; defaults to slot width - 0.3 (light push fit)",
    )
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    parts_out = out / OUTPUT_DIRECTORY
    parts_out.mkdir(parents=True, exist_ok=True)

    board = load_board(args.board)
    slots = board["slots"]
    pitch = slots["pitch_mm"]
    spec = load_spec()

    # The arch must span the rib with margin, otherwise the skirt cannot drop into
    # the neighbouring slot. Design against the largest measured rib.
    rib_max = slots.get("rib_max_mm", slots.get("rib_mm"))
    intrusion = 1.2
    required_span = rib_max + intrusion
    arch_scale = required_span / spec.arch_span

    # Retention is the skirt pressing on the slot edge, so the across-slot width
    # has to reach the edge. A light push fit, not the reference part's 16.0 mm.
    ring_width = args.ring_width if args.ring_width else slots["width_mm"] - 0.3

    manifest = {
        "code_version": CODE_VERSION,
        "output_directory": OUTPUT_DIRECTORY,
        "manifest": "manifest.json",
        "board": {
            "id": board["id"],
            "status": board.get("status"),
            "slot_w_mm": board["slots"]["width_mm"],
            "rib_w_mm": board["slots"]["rib_mm"],
            "pitch_mm": pitch,
            "sheet_t_mm": round(
                board["sheets"]["aluminium_mm"] + board["sheets"]["powder_coat_mm"], 3
            ),
            "under_sheet_clearance_mm": board["sheets"].get("under_sheet_clearance_mm"),
        },
        "keeper": {
            **spec.summary(),
            "ring_width_mm": round(ring_width, 2),
            "arch_scale": round(arch_scale, 4),
            "arch_span_mm": round(spec.scaled_arch_span(arch_scale), 2),
            "rib_max_mm": rib_max,
            "skirt_intrusion_mm": round(spec.scaled_arch_span(arch_scale) - rib_max, 2),
        },
        "arrangement_pitch_mm": pitch,
        "items": [],
    }

    parts: list[tuple[str, object, dict]] = [
        ("keeper_ring", build_ring(spec, arch_scale=arch_scale, width=ring_width), {})
    ]

    wanted = [int(x) for x in str(args.rings).split(",") if x.strip()]
    for n in sorted(set(wanted)):
        if n < 1:
            continue
        part, bar_len = build_arrangement(
            spec, rings=n, pitch=pitch, arch_scale=arch_scale, width=ring_width
        )
        parts.append(
            (
                f"keeper_arrangement_{n}ring",
                part,
                {"rings": n, "bar_len_mm": round(bar_len, 2), "pitch_mm": pitch},
            )
        )

    rc = 0
    for name, part, meta in parts:
        stl = parts_out / f"{name}.stl"
        step = parts_out / f"{name}.step" if args.step else None
        export(part, str(stl), str(step) if step else None)
        mesh = trimesh.load(str(stl), force="mesh")
        rep = report(mesh)
        single = len(part.solids()) == 1
        ok = rep["watertight"] and single
        print(f"[{'ok' if ok else 'FAIL'}] {name}")
        print(f"   size     {rep['extents_mm']}  volume {rep['volume_mm3']} mm3")
        if meta:
            print(f"   layout   {meta}")
        manifest["items"].append(
            {
                "part": name,
                "file": stl.relative_to(out).as_posix(),
                "step": step.relative_to(out).as_posix() if step else None,
                **meta,
                "mesh": rep,
                "single_solid": single,
            }
        )
        if not ok:
            rc = 1

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"\nring width {ring_width:.2f} mm in a {slots['width_mm']:.1f} mm slot"
        f"  ({slots['width_mm'] - ring_width:.2f} mm total clearance)"
    )
    print(
        f"arch span {spec.scaled_arch_span(arch_scale):.2f} mm "
        f"(rib max {rib_max:.2f} + {intrusion:.1f} intrusion, scale {arch_scale:.4f})"
    )
    print(f"manifest -> {out / 'manifest.json'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
