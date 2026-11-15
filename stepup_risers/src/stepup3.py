"""The StepUp-3 as a solid, so a riser's height can be read against it.

The cross-section is the sheet's own side profile, read off ``ref/StepUp-3.pdf``
sheet 3 of 3 (the lower-right drawing) and written down in
``cfg/stepup3.json``. It is one closed loop walked once - outer face out, inner
face back - so the 1 mm sheet thickness falls out of the two radii at each fold:

* the level top, 139.00 between the fold tangents, at 25.01
* a full-height front wall folded down at R2.00 and turned inboard into a foot
  flange at 9 deg
* the sheet turned under at the rear with R1.50 and run back inboard as a hem
  flange at the same 9 deg

Both flanges are on one 9 deg plane, so the part is open underneath: a hollow V
under a level deck, not a filled wedge. That is what the drawing shows and it is
what this builds.

Datum: origin at the centre of the footprint on the board's top face, +X along
the 255.00 length, +Y across the depth with the front wall at -Y, +Z up.

    .venv/Scripts/python stepup_risers/src/stepup3.py
    .venv/Scripts/python stepup_risers/src/stepup3.py --check
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from dataclasses import dataclass

import cadquery as cq

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CFG = PROJECT / "cfg"
DWG = PROJECT / "dwg"
DEFAULT_CONFIG = CFG / "stepup3.json"
DEFAULT_STL = DWG / "stepup3.stl"

LEN_TOL_MM = 0.02
THIN_TOL_MM = 0.01


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Spec:
    raw: dict
    id: str
    depth_mm: float
    height_mm: float
    sheet_mm: float
    underside_deg: float
    front_outer_mm: float
    front_inner_mm: float
    rear_outer_mm: float
    rear_inner_mm: float
    foot_strap_mm: float
    hem_strap_mm: float
    width_mm: float
    density_g_cm3: float

    @property
    def rad(self) -> float:
        return math.radians(self.underside_deg)


def load(path: pathlib.Path = DEFAULT_CONFIG) -> Spec:
    raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    p = raw["profile"]
    front_outer, front_inner = float(p["front_fold_outer_mm"]), float(
        p["front_fold_inner_mm"]
    )
    rear_outer, rear_inner = float(p["rear_fold_outer_mm"]), float(
        p["rear_fold_inner_mm"]
    )
    sheet = float(p["sheet_mm"])
    for name, outer, inner in (
        ("front", front_outer, front_inner),
        ("rear", rear_outer, rear_inner),
    ):
        if abs((outer - inner) - sheet) > THIN_TOL_MM:
            raise ValueError(
                f"{path.name}: the {name} folds are R{outer} / R{inner}, which is "
                f"{outer - inner:.3f} apart; the sheet is {sheet:.3f}"
            )
    if float(p["height_mm"]) <= 2.0 * front_outer:
        raise ValueError(f"{path.name}: the front folds do not fit the height")
    return Spec(
        raw=raw,
        id=str(raw["id"]),
        depth_mm=float(p["depth_mm"]),
        height_mm=float(p["height_mm"]),
        sheet_mm=sheet,
        underside_deg=float(p["underside_deg"]),
        front_outer_mm=front_outer,
        front_inner_mm=front_inner,
        rear_outer_mm=rear_outer,
        rear_inner_mm=rear_inner,
        foot_strap_mm=float(p["foot_strap_mm"]),
        hem_strap_mm=float(p["hem_strap_mm"]),
        width_mm=float(raw["width_mm"]),
        density_g_cm3=float(raw["material"]["density_g_cm3"]),
    )


# --------------------------------------------------------------------------- #
# the cross-section
# --------------------------------------------------------------------------- #


def profile_loop(spec: Spec) -> list[dict]:
    """The closed section as ordered primitives: lines and arcs, in the sheet's order.

    Coordinates are the drawing's own: x is depth with the front face at 0, y is
    height with the part's lowest point at 0.
    """
    a = spec.rad
    t = spec.sheet_mm
    h = spec.height_mm
    d = spec.depth_mm
    r_fo, r_fi = spec.front_outer_mm, spec.front_inner_mm
    r_ro, r_ri = spec.rear_outer_mm, spec.rear_inner_mm

    top = (r_fo, h - r_fo)  # front-top fold centre
    bot = (r_fo, r_fo)  # front-bottom fold centre
    rear = (d - r_ro, h - r_ro)  # rear fold centre

    # where the 9 deg underside leaves each fold, tangentially
    foot_start = (bot[0] + r_fo * math.sin(a), bot[1] - r_fo * math.cos(a))
    hem_start = (rear[0] + r_ro * math.sin(a), rear[1] - r_ro * math.cos(a))
    along = (math.cos(a), math.sin(a))
    up = (-math.sin(a), math.cos(a))  # normal to a flange, on the inside

    def off(p, v, k):
        return (p[0] + v[0] * k, p[1] + v[1] * k)

    hem_end_out = off(hem_start, along, -spec.hem_strap_mm)
    hem_end_in = off(hem_end_out, up, t)
    hem_in_start = off(rear, (-math.sin(a), -math.cos(a)), r_ri)
    foot_in_start = off(bot, (-math.sin(a), -math.cos(a)), r_fi)
    foot_end_in = off(foot_in_start, along, spec.foot_strap_mm)
    foot_end_out = off(foot_end_in, up, -t)

    a_rear = -90.0 + spec.underside_deg  # where the hem meets the rear fold
    return [
        # outer, going outboard along the top
        {"kind": "line", "to": (rear[0], h), "note": "top face"},
        {"kind": "arc", "centre": rear, "radius": r_ro, "start_deg": 90.0,
         "sweep_deg": -(180.0 - spec.underside_deg), "to": hem_start, "note": "rear fold"},
        {"kind": "line", "to": hem_end_out, "note": "hem outer face"},
        {"kind": "line", "to": hem_end_in, "note": "hem end face"},
        # inner, coming back
        {"kind": "line", "to": hem_in_start, "note": "hem inner face"},
        {"kind": "arc", "centre": rear, "radius": r_ri, "start_deg": a_rear,
         "sweep_deg": 180.0 - spec.underside_deg, "to": (rear[0], h - t), "note": "rear fold"},
        {"kind": "line", "to": (top[0], h - t), "note": "deck underside"},
        {"kind": "arc", "centre": top, "radius": r_fi, "start_deg": 90.0,
         "sweep_deg": 90.0, "to": (r_fi, top[1]), "note": "front top fold"},
        {"kind": "line", "to": (r_fi, bot[1]), "note": "front wall inner"},
        {"kind": "arc", "centre": bot, "radius": r_fi, "start_deg": 180.0,
         "sweep_deg": 90.0 + spec.underside_deg, "to": foot_in_start, "note": "front bottom fold"},
        {"kind": "line", "to": foot_end_in, "note": "foot inner face"},
        {"kind": "line", "to": foot_end_out, "note": "foot end face"},
        # outer again, back to the start
        {"kind": "line", "to": foot_start, "note": "foot outer face"},
        {"kind": "arc", "centre": bot, "radius": r_fo, "start_deg": a_rear,
         "sweep_deg": -(90.0 + spec.underside_deg), "to": (0.0, bot[1]),
         "note": "front bottom fold"},
        {"kind": "line", "to": (0.0, top[1]), "note": "front wall outer"},
        {"kind": "arc", "centre": top, "radius": r_fo, "start_deg": 180.0,
         "sweep_deg": -90.0, "to": (top[0], h), "note": "front top fold"},
    ]


def _place(prims: list[dict]) -> cq.Workplane:
    """Walk the primitives into a closed wire on the YZ plane (local x -> depth)."""
    start = prims[-1]["to"]
    wp = cq.Workplane("YZ").moveTo(*start)
    for pr in prims:
        if pr["kind"] == "line":
            wp = wp.lineTo(*pr["to"])
            continue
        cx, cy = pr["centre"]
        r = pr["radius"]
        a0 = pr["start_deg"]
        sw = pr["sweep_deg"]
        mid = (
            cx + r * math.cos(math.radians(a0 + sw / 2.0)),
            cy + r * math.sin(math.radians(a0 + sw / 2.0)),
        )
        wp = wp.threePointArc(mid, tuple(pr["to"]))
    return wp.close()


def build(spec: Spec) -> cq.Workplane:
    """Extrude the section across the length and centre it on the origin."""
    wire = _place(profile_loop(spec))
    solid = wire.extrude(spec.width_mm)
    return solid.translate((-spec.width_mm / 2.0, -spec.depth_mm / 2.0, 0.0)).clean()


def section_area(spec: Spec) -> float:
    """Cross-section area = centreline length x sheet.

    The loop's boundary runs the outer face out and the inner face back, so its
    perimeter is twice the centreline at any uniform thickness - the folds' inner
    and outer arc lengths average to the mid radius for free.
    """
    rad = math.radians
    t = spec.sheet_mm
    front_swing = 90.0 + spec.underside_deg
    rear_swing = 180.0 - spec.underside_deg
    wall = spec.height_mm - 2.0 * spec.front_outer_mm
    deck = spec.depth_mm - spec.front_outer_mm - spec.rear_outer_mm
    perimeter = (
        deck
        + rad(rear_swing) * spec.rear_outer_mm
        + spec.hem_strap_mm
        + t
        + spec.hem_strap_mm
        + rad(rear_swing) * spec.rear_inner_mm
        + deck
        + rad(90.0) * spec.front_inner_mm
        + wall
        + rad(front_swing) * spec.front_inner_mm
        + spec.foot_strap_mm
        + t
        + spec.foot_strap_mm
        + rad(front_swing) * spec.front_outer_mm
        + wall
        + rad(90.0) * spec.front_outer_mm
    )
    return perimeter / 2.0 * t


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


def _face_angles(solid: cq.Solid) -> tuple[float, float]:
    """(tilt of the largest upward face, tilt of the largest 9-deg-ish lower face)."""
    up = down = None
    for face in solid.Faces():
        if face.geomType() != "PLANE":
            continue
        n = face.normalAt()
        area = face.Area()
        if n.z > 0.9999:
            if up is None or area > up[0]:
                up = (area, 0.0)
        elif n.z < -0.5 and abs(n.y) > 0.01:
            tilt = math.degrees(math.asin(min(1.0, abs(n.y))))
            if down is None or area > down[0]:
                down = (area, tilt)
    return (up[1] if up else float("nan")), (down[1] if down else float("nan"))


def _thickness_at(solid: cq.Solid, y: float, z: float) -> float:
    """Vertical run of material through the deck at (y, z): the sheet thickness."""
    post = cq.Solid.makeCylinder(
        0.2, 60.0, cq.Vector(0.0, y, z - 30.0), cq.Vector(0, 0, 1)
    )
    hit = solid.intersect(post).Solids()
    return sum(s.BoundingBox().zlen for s in hit)


def validate(spec: Spec, shape: cq.Workplane) -> list[Check]:
    solid = shape.val()
    box = solid.BoundingBox()
    checks: list[Check] = []

    def exact(name, value, wanted, note="", tol=LEN_TOL_MM, unit="mm"):
        checks.append(
            Check(name, f"{value:.3f} {unit}", f"{wanted:.3f} {unit}",
                  abs(value - wanted) <= tol, note)
        )

    def flag(name, value, limit, ok, note=""):
        checks.append(Check(name, value, limit, bool(ok), note))

    exact("width", box.xlen, spec.width_mm, "255.00 printed on sheet 3 of 3")
    exact("depth", box.ylen, spec.depth_mm, "142.50 printed on the section")
    exact("height", box.zlen, spec.height_mm, "25.01 printed at the front wall")
    exact("stands on z = 0", box.zmin, 0.0, "the front fold's underside is the lowest point")

    top_tilt, under_tilt = _face_angles(solid)
    exact("top is level", top_tilt, 0.0, "the 9 deg callout is the flange, not the deck",
          unit="deg")
    exact("flange angle", under_tilt, spec.underside_deg,
          "the foot and the hem are collinear on this one plane", unit="deg")

    thick = _thickness_at(solid, 0.0, spec.height_mm - 5.0)
    exact("sheet thickness", thick, spec.sheet_mm, "measured vertically through the deck")

    area = section_area(spec)
    expected = area * spec.width_mm / 1000.0
    volume = solid.Volume() / 1000.0
    flag(
        "cross-section area",
        f"{area:.2f} mm2",
        "reported",
        abs(volume - expected) / expected < 0.01,
        f"centreline {area / spec.sheet_mm:.1f} x {spec.sheet_mm:g} sheet; the built solid "
        f"is {volume:.1f} cm3 against {expected:.1f} expected, "
        f"{volume * spec.density_g_cm3:.0f} g in {spec.raw['material']['id']}",
    )

    shells = solid.Shells()
    flag(
        "one closed shell",
        f"{len(shells)} shell(s), {sum(1 for s in shells if s.Closed())} closed",
        "1 closed",
        len(shells) == 1 and all(s.Closed() for s in shells),
        "the sheet is one solid with no voids in it: the hollow under the deck is open",
    )
    short = [e for e in solid.Edges() if e.Length() < 0.05]
    flag(
        "no sliver edges",
        f"{len(short)} under 0.05",
        "0",
        not short,
        "the folds have to come out tangent, or the loop closes on a knife edge",
    )
    return checks


# --------------------------------------------------------------------------- #
# report and command line
# --------------------------------------------------------------------------- #


def report(spec: Spec, checks: list[Check], out: pathlib.Path | None) -> str:
    lines = [
        f"{spec.id}{'  (' + pathlib.Path(out).name + ')' if out else ''}",
        "",
        f"  section               {spec.depth_mm:.2f} deep x {spec.height_mm:.2f} high, "
        f"{spec.sheet_mm:.2f} sheet, flanges at {spec.underside_deg:g} deg",
        f"  folds                 front R{spec.front_outer_mm:g}/R{spec.front_inner_mm:g}, "
        f"rear R{spec.rear_outer_mm:g}/R{spec.rear_inner_mm:g}",
        f"  length                {spec.width_mm:.2f}, one extrusion",
        "",
        "checks",
    ]
    width = max(len(c.name) for c in checks)
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        lines.append(
            f"  {mark} {c.name:<{width}}  {c.value:>20}  {c.limit:>16}  {c.note}"
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
    shape = build(spec)
    checks = validate(spec, shape)
    out = args.out or DEFAULT_STL

    if args.json:
        print(json.dumps(
            {"id": spec.id, "stl": str(out),
             "checks": [{"name": c.name, "value": c.value, "ok": c.ok} for c in checks],
             "ok": all(c.ok for c in checks)},
            indent=2))
    else:
        print(report(spec, checks, None if args.check else out))
    if not args.check:
        out.parent.mkdir(parents=True, exist_ok=True)
        cq.exporters.export(shape, str(out), tolerance=args.tolerance, angularTolerance=0.1)
        cq.exporters.export(shape, str(out.with_suffix(".step")))
        print(f"wrote {out}")
        print(f"wrote {out.with_suffix('.step')}")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
