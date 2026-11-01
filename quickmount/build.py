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
CODE_VERSION = "0.3.0"


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
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    board = load_board(args.board)
    pitch = board["slots"]["pitch_mm"]
    spec = load_spec()

    manifest = {
        "code_version": CODE_VERSION,
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
        "keeper": spec.summary(),
        "arrangement_pitch_mm": pitch,
        "items": [],
    }

    parts: list[tuple[str, object, dict]] = [("keeper_ring", build_ring(spec), {})]

    wanted = [int(x) for x in str(args.rings).split(",") if x.strip()]
    for n in sorted(set(wanted)):
        if n < 1:
            continue
        part, bar_len = build_arrangement(spec, rings=n, pitch=pitch)
        parts.append(
            (
                f"keeper_arrangement_{n}ring",
                part,
                {"rings": n, "bar_len_mm": round(bar_len, 2), "pitch_mm": pitch},
            )
        )

    rc = 0
    for name, part, meta in parts:
        stl = out / f"{name}.stl"
        step = out / f"{name}.step" if args.step else None
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
                "file": stl.name,
                "step": step.name if step else None,
                **meta,
                "mesh": rep,
                "single_solid": single,
            }
        )
        if not ok:
            rc = 1

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nmanifest -> {out / 'manifest.json'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
