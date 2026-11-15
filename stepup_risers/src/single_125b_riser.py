"""Tip the clip-free 125B base onto the PedalRiser's inclined deck.

Step two of the single-125B riser. Step one signed off the flat base plate; this
tips the plate about its side-row end and sets it on the PedalRiser's top surface
so its countersunk face is coplanar with that deck, its pair of close hole rows
riding up the slope. The short end reads the deck's 20 mm front and the long end
lands partway up the slope, exactly where the deck's own fall puts it.

Nothing about the plate is rebuilt here: it comes from ``single_125b.py``, which
takes it from the Type B1 plate. This module adds only the deck placement - the
tip and the lift - and checks that the countersunk face is on the deck and the
close hole rows are on the tall side. The previous tube-bearing export is kept
as ``dwg/screw_tubes.stl`` for comparison; tubes are not part of this generator.

Datum is the plate's own, carried through the placement: origin at the centre of
its board-facing face, +X across the 72 mm width, +Y along the 125.5 mm length
toward the close pair of hole rows, +Z from the board face toward the pedal. The
deck's front height, rear height and span are the knobs to adjust in
``cfg/single_125b_riser.json``.

    .venv/Scripts/python stepup_risers/src/single_125b_riser.py
    .venv/Scripts/python stepup_risers/src/single_125b_riser.py --check
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import pathlib
import sys
from dataclasses import dataclass

import cadquery as cq

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CFG = PROJECT / "cfg"
DWG = PROJECT / "dwg"
DEFAULT_CONFIG = CFG / "single_125b_riser.json"
DEFAULT_STL = DWG / "single_125b_riser.stl"

LEN_TOL_MM = 0.02


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Spec:
    raw: dict
    id: str
    plate_config: pathlib.Path
    front_height_mm: float
    rear_height_mm: float
    span_mm: float

    @property
    def slope(self) -> float:
        return (self.rear_height_mm - self.front_height_mm) / self.span_mm

    @property
    def slope_deg(self) -> float:
        return math.degrees(math.atan(self.slope))


def _read(path: pathlib.Path, what: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{what} is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module(name: str, path: pathlib.Path):
    """Import a sibling project's generator, so the riser is the real plate."""
    if not path.exists():
        raise FileNotFoundError(f"generator is missing: {path}")
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module


def load(path: pathlib.Path = DEFAULT_CONFIG) -> Spec:
    raw = _read(path, path.name)
    deck = raw["deck"]
    front = float(deck["front_height_mm"])
    rear = float(deck["rear_height_mm"])
    span = float(deck["span_mm"])
    pivot = str(deck.get("pivot", "front edge"))
    if not pivot.startswith("front edge"):
        raise ValueError(
            f"{path.name}: deck.pivot is {pivot!r}; only the front edge is built"
        )
    if not (rear > front > 0.0 and span > 0.0):
        raise ValueError(
            f"{path.name}: need rear_height_mm > front_height_mm > 0 and span_mm > 0"
        )
    return Spec(
        raw=raw,
        id=str(raw["id"]),
        plate_config=(CFG / raw["plate"]["config"]).resolve(),
        front_height_mm=front,
        rear_height_mm=rear,
        span_mm=span,
    )


# --------------------------------------------------------------------------- #
# the part
# --------------------------------------------------------------------------- #


def build(spec: Spec) -> dict:
    plate_module = _load_module("single_125b", PROJECT / "src" / "single_125b.py")
    plate_spec = plate_module.load(spec.plate_config)
    flat = plate_module.build_base(plate_spec)

    angle_deg = spec.slope_deg
    half = plate_spec.length_mm / 2.0

    # Tip the plate about its -Y end (the lone side row), so its +Y end - the
    # pair of close hole rows - rides up the slope to the deck's tall end.
    tipped = flat.rotate((0.0, -half, 0.0), (1.0, -half, 0.0), angle_deg)
    shift_y = (spec.span_mm - plate_spec.length_mm) / 2.0
    riser = tipped.translate((0.0, -shift_y, spec.front_height_mm)).clean()

    return {
        "parts": {"flat": flat, "riser": riser},
        "plate_spec": plate_spec,
        "angle_deg": angle_deg,
        "shift_y_mm": -shift_y,
        "rear_edge_mm": spec.front_height_mm
        + plate_spec.length_mm * math.sin(math.atan(spec.slope)),
    }


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


def _top_face(solid: cq.Solid):
    """The largest upward face: the pedal face of the placed plate."""
    best = None
    for face in solid.Faces():
        if face.geomType() != "PLANE":
            continue
        nz = face.normalAt().z
        if nz <= 0.5 or nz >= 0.99999:
            continue
        area = face.Area()
        if best is None or area > best[0]:
            best = (area, face)
    return best[1] if best else None


def _bottom_face(solid: cq.Solid):
    """The largest downward face: the board face carrying the counterbores."""
    best = None
    for face in solid.Faces():
        if face.geomType() != "PLANE":
            continue
        nz = face.normalAt().z
        if nz >= -0.5 or nz <= -0.99999:
            continue
        area = face.Area()
        if best is None or area > best[0]:
            best = (area, face)
    return best[1] if best else None


def _tilt_deg(face) -> float:
    return math.degrees(math.acos(min(1.0, face.normalAt().z)))


def validate(spec: Spec, built: dict) -> list[Check]:
    riser = built["parts"]["riser"].val()
    plate_spec = built["plate_spec"]
    checks: list[Check] = []

    slope = spec.slope
    rad = math.atan(slope)
    deg = math.degrees(rad)
    length = plate_spec.length_mm
    thickness = plate_spec.thickness_mm
    half = length / 2.0
    shift_y = (spec.span_mm - length) / 2.0

    def deck_z(y: float) -> float:
        return spec.front_height_mm + slope * (y + spec.span_mm / 2.0)

    def world_of(x: float, y: float, z: float) -> cq.Vector:
        """A plate-local point under the tip and lift."""
        yy = y + half
        y2 = -half + yy * math.cos(rad) - z * math.sin(rad)
        z2 = yy * math.sin(rad) + z * math.cos(rad)
        return cq.Vector(x, y2 - shift_y, spec.front_height_mm + z2)

    def exact(name, value, wanted, note="", tol=LEN_TOL_MM, unit="mm"):
        checks.append(
            Check(name, f"{value:.3f} {unit}", f"{wanted:.3f} {unit}",
                  abs(value - wanted) <= tol, note)
        )

    def flag(name, value, limit, ok, note=""):
        checks.append(Check(name, value, limit, bool(ok), note))

    box = riser.BoundingBox()

    # ---- the plate is on the deck ------------------------------------------ #
    exact("width", box.xlen, plate_spec.width_mm,
          "the 72 mm way is unchanged by the turn and tip")
    exact("plan length", box.ylen,
          length * math.cos(rad) + thickness * math.sin(rad),
          "125.50 tipped, plus the thickness's own lean")
    exact("overall height", box.zlen,
          length * math.sin(rad) + thickness * math.cos(rad),
          f"{length:.2f} x sin + {thickness:.2f} x cos")
    exact("short end on the deck front", box.zmin, spec.front_height_mm,
          "the side-row end is the pivot and is lifted to the deck's low edge")

    top = _top_face(riser)
    if top is not None:
        exact("deck slope", _tilt_deg(top), deg,
              "the pedal face falls at the deck's angle", unit="deg")

    bottom = _bottom_face(riser)
    if bottom is not None:
        n = bottom.normalAt()
        c = bottom.Center()
        flag(
            "bottom face normal matches the deck",
            f"({n.x:.3f}, {n.y:.3f}, {n.z:.3f})",
            f"(0, {math.sin(rad):.3f}, {-math.cos(rad):.3f})",
            abs(n.x) <= 0.05 and abs(n.y - math.sin(rad)) <= 0.05
            and abs(n.z + math.cos(rad)) <= 0.05,
            "the board face points down and toward the deck's tall end",
        )
        exact("bottom face lies on the deck", c.z, deck_z(c.y),
              "a point on the board face satisfies the deck's plane")

    # ---- the close pair of hole rows has to be on the tall side -------------- #
    clearance = next(p for p in plate_spec.patterns if p.id == "clearance")
    side = next(p for p in plate_spec.patterns if p.id == "side")
    z_clear = world_of(clearance.x_mm, clearance.y_mm, thickness / 2.0).z
    z_side = world_of(side.x_mm, side.y_mm, thickness / 2.0).z
    flag(
        "close hole rows on the tall side",
        f"clearance row {z_clear:.2f} vs side row {z_side:.2f} mm",
        "clearance higher",
        z_clear > z_side + 1.0,
        "the Ø4 + Ø3.5 pair at the plate's +Y end rides up to the deck's 40 mm tall end",
    )

    # ---- not flipped: the counterbores are still underneath ----------------- #
    counterbore = next(p for p in plate_spec.patterns if p.face_mm)
    r_face = (counterbore.face_mm or 0.0) / 2.0
    depth_face = float(counterbore.face_depth_mm)
    normal = cq.Vector(0.0, math.sin(rad), -math.cos(rad))  # plate -Z in world

    def void_at(point: cq.Vector) -> bool:
        probe = cq.Solid.makeCylinder(0.25, 0.3, point - normal * 0.15, normal)
        return not riser.intersect(probe).Solids()

    recess_down = []
    for pattern in plate_spec.patterns:
        if pattern.id != counterbore.id:
            continue
        for x, y in pattern.positions:
            open_below = void_at(world_of(x + r_face - 0.4, y, 0.3))
            solid_above = not void_at(world_of(x + r_face - 0.4, y, depth_face + 0.6))
            if open_below and solid_above:
                recess_down.append((x, y))
    flag(
        "countersinks face down",
        f"{len(recess_down)}/{len(counterbore.positions)} under the plate",
        f"{len(counterbore.positions)}",
        len(recess_down) == len(counterbore.positions),
        f"each D{counterbore.face_mm:g} x {depth_face:g} recess is open from below and "
        "solid above it, so the plate is tipped and not flipped",
    )

    shells = riser.Shells()
    flag(
        "one closed shell",
        f"{len(shells)} shell(s), {sum(1 for s in shells if s.Closed())} closed",
        "1 closed",
        len(shells) == 1 and all(s.Closed() for s in shells),
        "the tube-free plate is one body",
    )
    flag(
        "tall edge height",
        f"{box.zmax:.2f} mm",
        "reported",
        True,
        f"{box.zmax:.2f}: the plate's top corner above the deck, against the "
        f"PedalRiser's drawn 41.00",
    )
    return checks


# --------------------------------------------------------------------------- #
# report and command line
# --------------------------------------------------------------------------- #


def report(spec: Spec, built: dict, checks: list[Check], out: pathlib.Path | None) -> str:
    box = built["parts"]["riser"].val().BoundingBox()
    plate_spec = built["plate_spec"]
    lines = [
        f"{spec.id}{'  (' + pathlib.Path(out).name + ')' if out else ''}",
        "",
        f"  plate                 {plate_spec.length_mm:.2f} x {plate_spec.width_mm:.2f} x "
        f"{plate_spec.thickness_mm:.2f}, Type B1 outline, clips removed",
        f"  deck                  front {spec.front_height_mm:.2f} / rear {spec.rear_height_mm:.2f} "
        f"over {spec.span_mm:.2f}, slope {built['angle_deg']:.2f} deg",
        "  placed                tipped about its side-row end, close hole rows ride "
        f"up the slope, shifted {built['shift_y_mm']:+.2f} in y, lifted to "
        f"{spec.front_height_mm:.2f}",
        f"  tall edge             {built['rear_edge_mm']:.2f} on the deck's fall",
        "  attachment            open design question; tube geometry is saved separately",
        f"  envelope              {box.xlen:.2f} x {box.ylen:.2f} x {box.zlen:.2f} "
        f"(z {box.zmin:.2f} .. {box.zmax:.2f})",
        "",
        "checks",
    ]
    width = max(len(c.name) for c in checks)
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        lines.append(
            f"  {mark} {c.name:<{width}}  {c.value:>28}  {c.limit:>16}  {c.note}"
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
    ap.add_argument("--part", choices=("riser", "flat"), default="riser")
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
    out = args.out or (DEFAULT_STL if args.part == "riser" else DWG / "single_125b_flat.stl")

    if args.json:
        print(json.dumps(
            {"id": spec.id, "stl": str(out),
             "checks": [{"name": c.name, "value": c.value, "ok": c.ok} for c in checks],
             "ok": all(c.ok for c in checks)}, indent=2))
    else:
        print(report(spec, built, checks, None if args.check else out))
    if not args.check:
        out.parent.mkdir(parents=True, exist_ok=True)
        shape = built["parts"][args.part]
        cq.exporters.export(shape, str(out), tolerance=args.tolerance, angularTolerance=0.1)
        cq.exporters.export(shape, str(out.with_suffix(".step")))
        print(f"wrote {out}")
        print(f"wrote {out.with_suffix('.step')}")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
