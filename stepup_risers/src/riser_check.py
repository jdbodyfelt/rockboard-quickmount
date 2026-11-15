"""The single-125B riser beside the PedalRiser, on one datum.

Not a part: a layout that stands the tipped 125B plate next to the PedalRiser it
is set against. Both share the same datum - the deck's 20.00 mm front, the
PedalRiser's metal bottom at z = 0 - so the plate's front, slope and height can be
read straight off the reference product.

Both bodies come from their own generators, so neither can drift from the part it
stands for; the board is not drawn, only the two parts side by side.

    .venv/Scripts/python stepup_risers/src/riser_check.py
    .venv/Scripts/python stepup_risers/src/riser_check.py --check
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
from dataclasses import dataclass

import cadquery as cq

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CFG = PROJECT / "cfg"
DWG = PROJECT / "dwg"
DEFAULT_CONFIG = CFG / "riser_check.json"
DEFAULT_STL = DWG / "riser-check.stl"

LEN_TOL_MM = 0.02


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PartRef:
    key: str
    generator: pathlib.Path
    config: pathlib.Path
    part: str | None


@dataclass(frozen=True)
class Spec:
    raw: dict
    id: str
    parts: dict[str, PartRef]
    order: tuple[str, ...]
    gap_mm: float


def _read(path: pathlib.Path, what: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{what} is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module(name: str, path: pathlib.Path):
    """Import a sibling generator, so the check builds the real parts."""
    if not path.exists():
        raise FileNotFoundError(f"generator is missing: {path}")
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module


def load(path: pathlib.Path = DEFAULT_CONFIG) -> Spec:
    raw = _read(path, path.name)
    parts = {
        key: PartRef(
            key=key,
            generator=PROJECT / "src" / node["generator"],
            config=(CFG / node["config"]).resolve(),
            part=None if node.get("part") is None else str(node["part"]),
        )
        for key, node in raw["parts"].items()
    }
    order = tuple(str(k) for k in raw["layout"]["order"])
    missing = [k for k in order if k not in parts]
    if missing:
        raise KeyError(f"{path.name}: layout.order names {missing}, which are not parts")
    return Spec(
        raw=raw,
        id=str(raw["id"]),
        parts=parts,
        order=order,
        gap_mm=float(raw["layout"]["gap_mm"]),
    )


# --------------------------------------------------------------------------- #
# the assembly
# --------------------------------------------------------------------------- #


def build(spec: Spec) -> dict:
    built: dict[str, cq.Workplane] = {}
    part_specs = {}
    for key in spec.order:
        ref = spec.parts[key]
        module = _load_module(f"_ck_{key}", ref.generator)
        obj_spec = module.load(ref.config)
        result = module.build(obj_spec)
        if isinstance(result, dict) and "parts" in result:
            part = result["parts"][ref.part]
        else:
            part = result
        built[key] = part
        part_specs[key] = obj_spec

    boxes = {k: v.val().BoundingBox() for k, v in built.items()}
    total = sum(b.xlen for b in boxes.values()) + spec.gap_mm * (len(spec.order) - 1)
    x = -total / 2.0
    parts: dict[str, cq.Workplane] = {}
    for key in spec.order:
        box = boxes[key]
        dx = (x + box.xlen / 2.0) - (box.xmin + box.xmax) / 2.0
        parts[key] = built[key].translate((dx, 0.0, 0.0))
        x += box.xlen + spec.gap_mm
    return {"parts": parts, "part_specs": part_specs}


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #


@dataclass
class Check:
    name: str
    value: str
    limit: str
    ok: bool
    note: str = ""


def validate(spec: Spec, built: dict) -> list[Check]:
    parts = built["parts"]
    boxes = {k: v.val().BoundingBox() for k, v in parts.items()}
    pedal_spec = built["part_specs"]["pedal_riser"]
    riser_spec = built["part_specs"]["riser"]
    pedal = boxes["pedal_riser"]
    riser = boxes["riser"]
    checks: list[Check] = []

    def flag(name, value, limit, ok, note=""):
        checks.append(Check(name, value, limit, bool(ok), note))

    flag(
        "fronts share the deck's 20.00",
        f"riser front {riser_spec.front_height_mm:.2f} vs pedal front {pedal_spec.front_edge_mm:.2f}",
        f"{pedal_spec.front_edge_mm:.2f}",
        abs(riser_spec.front_height_mm - pedal_spec.front_edge_mm) <= LEN_TOL_MM,
        "the plate's short edge and the PedalRiser's front wall read the same height",
    )

    overlaps = []
    for i, a in enumerate(spec.order):
        for b in spec.order[i + 1:]:
            if boxes[a].xmax > boxes[b].xmin and boxes[b].xmax > boxes[a].xmin:
                overlaps.append(f"{a}/{b}")
    flag(
        "the two parts do not overlap",
        f"{len(overlaps)} overlap(s)",
        "0",
        not overlaps,
        f"laid out {spec.gap_mm:g} apart in the order {' / '.join(spec.order)}",
    )

    lo = min(b.xmin for b in boxes.values())
    hi = max(b.xmax for b in boxes.values())
    flag(
        "the row is centred",
        f"{(lo + hi) / 2.0:.2f}",
        "0.00",
        abs((lo + hi) / 2.0) <= LEN_TOL_MM,
        "the pair straddles x = 0",
    )

    flag(
        "plate slope against the deck",
        f"{riser_spec.slope_deg:.2f} vs {pedal_spec.slope_deg:.2f} deg",
        "reported",
        True,
        f"{riser_spec.slope_deg - pedal_spec.slope_deg:+.2f} deg: the 40.0 knob is one "
        "short of the drawn 41.0, so the plate falls a touch shallower than the deck",
    )
    return checks


# --------------------------------------------------------------------------- #
# report and command line
# --------------------------------------------------------------------------- #


def report(spec: Spec, built: dict, checks: list[Check], out: pathlib.Path | None) -> str:
    boxes = {k: v.val().BoundingBox() for k, v in built["parts"].items()}
    lines = [
        f"{spec.id}{'  (' + pathlib.Path(out).name + ')' if out else ''}",
        "",
        f"  {'part':<12}{'x':>9}{'y':>9}{'z':>9}{'x centre':>11}{'z top':>8}",
    ]
    for key in spec.order:
        b = boxes[key]
        lines.append(
            f"  {key:<12}{b.xlen:>9.2f}{b.ylen:>9.2f}{b.zlen:>9.2f}"
            f"{(b.xmin + b.xmax) / 2.0:>11.2f}{b.zmax:>8.2f}"
        )
    lines += ["", "checks"]
    width = max(len(c.name) for c in checks)
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        lines.append(
            f"  {mark} {c.name:<{width}}  {c.value:>34}  {c.limit:>12}  {c.note}"
        )
    failed = [c for c in checks if not c.ok]
    lines.append("")
    lines.append(
        f"{len(checks) - len(failed)}/{len(checks)} checks pass"
        if not failed
        else f"{len(failed)} CHECK(S) FAILED"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tolerance", type=float, default=0.01)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    spec = load(args.config)
    built = build(spec)
    checks = validate(spec, built)
    out = args.out or DEFAULT_STL

    if args.json:
        print(json.dumps(
            {"id": spec.id, "stl": str(out),
             "checks": [{"name": c.name, "value": c.value, "ok": c.ok} for c in checks],
             "ok": all(c.ok for c in checks)}, indent=2))
    else:
        print(report(spec, built, checks, None if args.check else out))

    if not args.check:
        out.parent.mkdir(parents=True, exist_ok=True)
        shape = cq.Workplane(
            obj=cq.Compound.makeCompound([v.val() for v in built["parts"].values()])
        )
        cq.exporters.export(shape, str(out), tolerance=args.tolerance, angularTolerance=0.1)
        cq.exporters.export(shape, str(out.with_suffix(".step")))
        print(f"wrote {out}")
        print(f"wrote {out.with_suffix('.step')}")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
