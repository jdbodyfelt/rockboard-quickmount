"""Build all catalog pedals into printable STLs.

Usage: python -m quickmount.build [--out out] [--step]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import trimesh
import yaml

from .plate import (
    BoardProfile,
    PedalProfile,
    PlateOptions,
    build_plate,
    export,
    layout,
    to_print_orientation,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
CODE_VERSION = "0.1.0"


def load_yaml(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_board(name: str = "quad_4x") -> tuple[BoardProfile, dict]:
    raw = load_yaml(CATALOG / "boards" / f"{name}.yaml")
    board = BoardProfile(
        slot_w=raw["slots"]["width_mm"],
        rib_w=raw["slots"]["rib_mm"],
        pitch=raw["slots"]["pitch_mm"],
        sheet_t=raw["sheets"]["aluminium_mm"] + raw["sheets"]["powder_coat_mm"],
    )
    return board, raw


def load_pedal(path: pathlib.Path) -> tuple[PedalProfile, dict]:
    raw = load_yaml(path)
    pedal = PedalProfile(
        pedal_id=raw["id"],
        width=raw["physical"]["width_mm"],
        depth=raw["physical"]["depth_mm"],
        screw_inset=raw["pedal_screws"]["inset_mm"],
        screw_head_od=raw["pedal_screws"]["head_od_mm"],
        screw_count=raw["pedal_screws"].get("count", 4),
    )
    return pedal, raw


def geometry_report(mesh: trimesh.Trimesh) -> dict:
    return {
        "triangles": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "volume_mm3": round(float(mesh.volume), 1),
        "extents_mm": [round(float(v), 2) for v in mesh.extents],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "out"))
    ap.add_argument("--board", default="quad_4x")
    ap.add_argument("--step", action="store_true")
    ap.add_argument("--pedal", action="append", default=None, help="pedal id or yaml stem")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    board, board_raw = load_board(args.board)
    opt = PlateOptions()

    pedal_paths = sorted((CATALOG / "pedals").glob("*.yaml"))
    if args.pedal:
        wanted = set(args.pedal)
        pedal_paths = [p for p in pedal_paths if p.stem in wanted or p.stem in wanted]

    manifest = {
        "code_version": CODE_VERSION,
        "board": {
            "id": board_raw["id"],
            "status": board_raw["status"],
            "slot_w_mm": board.slot_w,
            "rib_w_mm": board.rib_w,
            "pitch_mm": board.pitch,
            "sheet_t_mm": round(board.sheet_t, 3),
        },
        "plate_options": opt.__dict__,
        "items": [],
    }

    rc = 0
    for path in pedal_paths:
        pedal, pedal_raw = load_pedal(path)
        try:
            part, lay = build_plate(pedal, board, opt)
            printable = to_print_orientation(part, opt)
            revision = hashlib.sha256(
                json.dumps(
                    {
                        "code": CODE_VERSION,
                        "pedal": pedal.pedal_id,
                        "board": board_raw["id"],
                        "opt": opt.__dict__,
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest()[:8]
            stem = f"{pedal.pedal_id}__{board_raw['id']}__petg__r{revision}"
            stl_path = out / f"{stem}.stl"
            step_path = out / f"{stem}.step" if args.step else None
            export(printable, str(stl_path), str(step_path) if step_path else None)
            mesh = trimesh.load(str(stl_path), force="mesh")
            report = geometry_report(mesh)
            status = "ok" if report["watertight"] else "NOT WATERTIGHT"
            if not report["watertight"]:
                rc = 1
            print(f"[{status}] {pedal.pedal_id}")
            print(f"   file     {stl_path.name}")
            print(f"   layout   {lay.as_dict()}")
            print(f"   mesh     {report}")
            manifest["items"].append(
                {
                    "pedal": pedal.pedal_id,
                    "model": pedal_raw["model"],
                    "file": stl_path.name,
                    "step": step_path.name if step_path else None,
                    "layout": lay.as_dict(),
                    "mesh": report,
                    "status": status,
                }
            )
        except Exception as exc:  # keep the batch alive
            rc = 1
            print(f"[FAILED] {pedal.pedal_id}: {exc}")
            manifest["items"].append({"pedal": pedal.pedal_id, "status": f"failed: {exc}"})

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nmanifest -> {out / 'manifest.json'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
