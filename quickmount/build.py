"""Build printable parts from the catalog.

Emits:
  * the reference clip, reproduced from its measured cross-section
  * a baseplate per catalog pedal, carrying that same hook section

Usage: python -m quickmount.build [--out out] [--step] [--board cinque_5_2]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import trimesh
import yaml

from .clip import (
    build_plate_with_clip,
    build_reference_clip,
    export,
    load_profile,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
CODE_VERSION = "0.2.0"


def load_yaml(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_board(name: str) -> dict:
    return load_yaml(CATALOG / "boards" / f"{name}.yaml")


def load_pedal(path: pathlib.Path) -> dict:
    return load_yaml(path)


def report(mesh: trimesh.Trimesh) -> dict:
    return {
        "triangles": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "volume_mm3": round(float(mesh.volume), 1),
        "extents_mm": [round(float(v), 2) for v in mesh.extents],
    }


def hook_stations(plate_d: float, screw_y: float, half_len: float = 16.0) -> tuple[float, ...]:
    """Two hook lines, clear of the pedal screws and of the plate ends."""
    y = plate_d / 2.0 - half_len - 8.0
    return (-y, y)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "out"))
    ap.add_argument("--board", default="cinque_5_2")
    ap.add_argument("--step", action="store_true")
    ap.add_argument("--pedal", action="append", default=None)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    board = load_board(args.board)
    clip = load_profile()

    manifest = {
        "code_version": CODE_VERSION,
        "board": {
            "id": board["id"],
            "status": board.get("status"),
            "slot_w_mm": board["slots"]["width_mm"],
            "rib_w_mm": board["slots"]["rib_mm"],
            "pitch_mm": board["slots"]["pitch_mm"],
            "sheet_t_mm": round(
                board["sheets"]["aluminium_mm"] + board["sheets"]["powder_coat_mm"], 3
            ),
        },
        "clip": {
            "id": "reference_2space_clip",
            "width_mm": clip.width,
            "span_x_mm": [round(v, 2) for v in clip.span_x],
            "depth_below_bar_mm": round(clip.depth_below_bar, 2),
            "hook_centres_x_mm": list(clip.hook_centres_x),
        },
        "items": [],
    }

    rc = 0

    replica = build_reference_clip(clip)
    stl = out / "clip_reference_2space.stl"
    step = out / "clip_reference_2space.step" if args.step else None
    export(replica, str(stl), str(step) if step else None)
    mesh = trimesh.load(str(stl), force="mesh")
    rep = report(mesh)
    print(f"[{'ok' if rep['watertight'] else 'LEAK'}] clip_reference_2space")
    print(f"   mesh     {rep}")
    manifest["items"].append(
        {
            "part": "clip_reference_2space",
            "file": stl.name,
            "step": step.name if step else None,
            "mesh": rep,
        }
    )
    if not rep["watertight"]:
        rc = 1

    paths = sorted((CATALOG / "pedals").glob("*.yaml"))
    if args.pedal:
        wanted = set(args.pedal)
        paths = [p for p in paths if p.stem in wanted]

    for path in paths:
        raw = load_pedal(path)
        pid = raw["id"]
        try:
            width = raw["physical"]["width_mm"]
            depth = raw["physical"]["depth_mm"]
            plate_w = width - 1.0
            plate_d = depth - 1.0
            inset = raw["pedal_screws"]["inset_mm"]
            hx = width / 2.0 - inset
            hy = depth / 2.0 - inset
            screws = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
            stations = hook_stations(plate_d, hy)

            part = build_plate_with_clip(
                plate_w=plate_w,
                plate_d=plate_d,
                t_plate=3.0,
                screw_xy=screws,
                screw_head_od=raw["pedal_screws"]["head_od_mm"],
                hook_stations_y=stations,
                mount_mode="bar_on_sheet",
                clip=clip,
                pitch_mm=board["slots"]["pitch_mm"],
            )
            rev = hashlib.sha256(
                json.dumps(
                    {"code": CODE_VERSION, "pedal": pid, "board": board["id"]},
                    sort_keys=True,
                ).encode()
            ).hexdigest()[:8]
            stem = f"{pid}__{board['id']}__petg__r{rev}"
            stl = out / f"{stem}.stl"
            step = out / f"{stem}.step" if args.step else None
            export(part, str(stl), str(step) if step else None)
            mesh = trimesh.load(str(stl), force="mesh")
            rep = report(mesh)
            ok = rep["watertight"]
            print(f"[{'ok' if ok else 'LEAK'}] {pid}")
            print(f"   file     {stl.name}")
            print(f"   hooks    y={[round(v, 2) for v in stations]}  x=+/-16.45 (1 pitch)")
            print(f"   mesh     {rep}")
            manifest["items"].append(
                {
                    "part": pid,
                    "file": stl.name,
                    "step": step.name if step else None,
                    "hook_stations_y_mm": [round(v, 2) for v in stations],
                    "screw_xy_mm": [[round(x, 2), round(y, 2)] for x, y in screws],
                    "mesh": rep,
                }
            )
            if not ok:
                rc = 1
        except Exception as exc:
            rc = 1
            print(f"[FAILED] {pid}: {exc}")
            manifest["items"].append({"part": pid, "status": f"failed: {exc}"})

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nmanifest -> {out / 'manifest.json'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
