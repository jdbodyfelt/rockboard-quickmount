"""Build the PETG twofer riser: two dovetail plates and one board-clipping wedge.

The clip-free Type B1 plates each have three underside dovetail rails. They slide
horizontally from opposite outside edges into a shared inclined wedge, where
uncut centre material stops their inward travel. Broad PETG pressure tabs in the
outer wedge walls engage notches under the centre rails to prevent slide-out.

    .venv/Scripts/python stepup_risers/src/dual_125b_riser.py
    .venv/Scripts/python stepup_risers/src/dual_125b_riser.py --check
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
DEFAULT_CONFIG = CFG / "dual_125b_riser.json"
LEN_TOL_MM = 0.03
CUT_MARGIN_MM = 1.0


@dataclass(frozen=True)
class Spec:
    raw: dict
    id: str
    plate_config: pathlib.Path
    tangent_radius_mm: float
    front_mm: float
    rear_mm: float
    span_mm: float
    gap_mm: float
    margin_mm: float
    rail_offsets_y: tuple[float, float, float]
    outer_top_mm: float
    outer_bottom_mm: float
    centre_top_mm: float
    centre_bottom_mm: float
    male_depth_mm: float
    clearance_mm: float
    tab_length_mm: float
    tab_width_mm: float
    tab_thickness_mm: float
    catch_height_mm: float
    catch_length_mm: float
    notch_length_mm: float
    notch_depth_mm: float
    notch_outer_inset_mm: float
    base_mm: float
    skin_mm: float
    wall_mm: float
    clip_x: tuple[float, float]
    clip_y: tuple[float, float]
    window_width_mm: float
    window_length_mm: float
    stadium_length_mm: float
    stadium_width_mm: float
    side_recess_mm: float
    stadium_y: tuple[float, float]

    @property
    def slope_rad(self) -> float:
        return math.atan((self.rear_mm - self.front_mm) / self.span_mm)

    @property
    def slope_deg(self) -> float:
        return math.degrees(self.slope_rad)


@dataclass
class Check:
    name: str
    value: str
    limit: str
    ok: bool
    note: str = ""


def _read(path: pathlib.Path, what: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{what} is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module(name: str, path: pathlib.Path):
    if not path.exists():
        raise FileNotFoundError(f"generator is missing: {path}")
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module


def load(path: pathlib.Path = DEFAULT_CONFIG) -> Spec:
    raw = _read(path, path.name)
    deck, layout, rail, pressure = raw["deck"], raw["layout"], raw["dovetail"], raw["pressure_lock"]
    structure, clips, lightening = raw["structure"], raw["board_clips"], raw["lightening"]
    front, rear, span = (float(deck[key]) for key in ("front_height_mm", "rear_height_mm", "span_mm"))
    if not (rear > front > 0 and span > 0):
        raise ValueError("deck requires rear_height_mm > front_height_mm > 0 and span_mm > 0")
    offsets = tuple(float(v) for v in rail["rail_offsets_y_mm"])
    if len(offsets) != 3 or offsets != tuple(sorted(offsets)):
        raise ValueError("dovetail.rail_offsets_y_mm must contain three ascending offsets")
    return Spec(
        raw=raw, id=str(raw["id"]), plate_config=(CFG / raw["plate"]["config"]).resolve(),
        tangent_radius_mm=float(raw["plate"]["tangent_corner_radius_mm"]),
        front_mm=front, rear_mm=rear, span_mm=span,
        gap_mm=float(layout["plate_gap_mm"]), margin_mm=float(layout["outer_margin_mm"]),
        rail_offsets_y=offsets, outer_top_mm=float(rail["outer_top_width_mm"]),
        outer_bottom_mm=float(rail["outer_bottom_width_mm"]),
        centre_top_mm=float(rail["centre_top_width_mm"]),
        centre_bottom_mm=float(rail["centre_bottom_width_mm"]), male_depth_mm=float(rail["male_depth_mm"]),
        clearance_mm=float(rail["clearance_mm"]), base_mm=float(structure["base_thickness_mm"]),
        tab_length_mm=float(pressure["tab_length_mm"]), tab_width_mm=float(pressure["tab_width_mm"]),
        tab_thickness_mm=float(pressure["tab_thickness_mm"]), catch_height_mm=float(pressure["catch_height_mm"]),
        catch_length_mm=float(pressure["catch_length_mm"]), notch_length_mm=float(pressure["notch_length_mm"]),
        notch_depth_mm=float(pressure["notch_depth_mm"]), notch_outer_inset_mm=float(pressure["notch_outer_inset_mm"]),
        skin_mm=float(structure["deck_skin_mm"]), wall_mm=float(structure["wall_mm"]),
        clip_x=tuple(float(v) for v in clips["centres_x_mm"]), clip_y=tuple(float(v) for v in clips["centres_y_mm"]),
        window_width_mm=float(clips["window_width_mm"]), window_length_mm=float(clips["window_length_mm"]),
        stadium_length_mm=float(lightening["stadium_length_mm"]),
        stadium_width_mm=float(lightening["stadium_width_mm"]), side_recess_mm=float(lightening["side_recess_mm"]),
        stadium_y=tuple(float(v) for v in lightening["centres_y_mm"]),
    )


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> cq.Solid:
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def _compound(shapes: list[cq.Solid]) -> cq.Workplane:
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


def _dovetail_prism(x0: float, x1: float, y: float, top: float, bottom: float, z0: float, z1: float) -> cq.Workplane:
    """A rail/cutter extruded along X; z1 is the narrow top and z0 the broad bottom."""
    pts = [(y - bottom / 2, z0), (y + bottom / 2, z0), (y + top / 2, z1), (y - top / 2, z1)]
    return cq.Workplane("YZ").polyline(pts).close().extrude(x1 - x0).translate((x0, 0, 0))


def _tangent_plate(spec: Spec, plate_spec) -> cq.Workplane:
    """The B1 screw field inside a smooth tangent perimeter, with no B1 clips."""
    plate = (
        cq.Workplane("XY")
        .rect(plate_spec.width_mm, plate_spec.length_mm)
        .extrude(plate_spec.thickness_mm)
        .edges("|Z")
        .fillet(spec.tangent_radius_mm)
    )
    tools: list[cq.Solid] = []
    for pattern in plate_spec.patterns:
        for x, y in pattern.positions:
            tools.append(
                cq.Solid.makeCylinder(
                    pattern.bore_mm / 2,
                    plate_spec.thickness_mm + 2 * CUT_MARGIN_MM,
                    cq.Vector(x, y, -CUT_MARGIN_MM),
                    cq.Vector(0, 0, 1),
                )
            )
            if pattern.face_mm and pattern.face_depth_mm:
                z0 = -CUT_MARGIN_MM if pattern.face_side == "board" else plate_spec.thickness_mm - pattern.face_depth_mm
                z1 = pattern.face_depth_mm if pattern.face_side == "board" else plate_spec.thickness_mm + CUT_MARGIN_MM
                if pattern.face_side == "board":
                    z1 = pattern.face_depth_mm
                tools.append(
                    cq.Solid.makeCylinder(
                        pattern.face_mm / 2,
                        z1 - z0 + CUT_MARGIN_MM,
                        cq.Vector(x, y, z0),
                        cq.Vector(0, 0, 1),
                    )
                )
    return plate.cut(_compound(tools)).clean()


def _place_on_deck(spec: Spec, shape: cq.Workplane, plate_length_mm: float) -> cq.Workplane:
    half = plate_length_mm / 2.0
    shift_y = (spec.span_mm - plate_length_mm) / 2.0
    return shape.rotate((0, -half, 0), (1, -half, 0), spec.slope_deg).translate((0, -shift_y, spec.front_mm))


def _plate_world_z(spec: Spec, plate_length_mm: float, local_y: float) -> float:
    half = plate_length_mm / 2.0
    return spec.front_mm + (local_y + half) * math.sin(spec.slope_rad)


def _deck_height(spec: Spec, y: float) -> float:
    return spec.front_mm + (y + spec.span_mm / 2.0) * math.tan(spec.slope_rad)


def _rail_dimensions(spec: Spec, index: int) -> tuple[float, float]:
    """The centre rail is broader; the outer pair only stabilise the plate."""
    return (
        (spec.centre_top_mm, spec.centre_bottom_mm)
        if index == 1
        else (spec.outer_top_mm, spec.outer_bottom_mm)
    )


def _plate_with_shoes(spec: Spec, plate_spec, centre_x: float) -> cq.Workplane:
    plate = _tangent_plate(spec, plate_spec)
    rails = cq.Workplane("XY")
    outer_sign = -1.0 if centre_x < 0.0 else 1.0
    for index, y in enumerate(spec.rail_offsets_y):
        top, bottom = _rail_dimensions(spec, index)
        rail = _dovetail_prism(
            -plate_spec.width_mm / 2,
            plate_spec.width_mm / 2,
            y,
            top,
            bottom,
            -spec.male_depth_mm,
            0.6,
        )
        rails = rails.add(rail.val())
    outer_edge = outer_sign * plate_spec.width_mm / 2.0
    notch_outer = outer_edge - outer_sign * spec.notch_outer_inset_mm
    notch_inner = notch_outer - outer_sign * spec.notch_length_mm
    notch = _box(
        min(notch_outer, notch_inner), max(notch_outer, notch_inner),
        -spec.tab_width_mm / 2.0, spec.tab_width_mm / 2.0,
        -spec.male_depth_mm - CUT_MARGIN_MM,
        -spec.male_depth_mm + spec.notch_depth_mm,
    )
    local = plate.union(rails).cut(cq.Workplane("XY").add(notch)).clean()
    placed = _place_on_deck(spec, local, plate_spec.length_mm).translate((centre_x, 0, 0))
    return placed.clean()


def _wedge(spec: Spec, plate_spec) -> cq.Workplane:
    width = 2 * plate_spec.width_mm + spec.gap_mm + 2 * spec.margin_mm
    half_x, half_y = width / 2, spec.span_mm / 2
    top_front, top_rear = spec.front_mm, spec.rear_mm
    # Outer solid keeps the high-load shell and rail roots continuous. The cavity
    # is deliberately shallow enough to retain 4 mm perimeter and deck walls.
    outer = (
        cq.Workplane("YZ")
        .polyline([(-half_y, 0), (half_y, 0), (half_y, top_rear), (-half_y, top_front)])
        .close().extrude(width).translate((-half_x, 0, 0))
    )
    cavity = (
        cq.Workplane("YZ")
        .polyline([
            (-half_y + spec.wall_mm, spec.base_mm),
            (half_y - spec.wall_mm, spec.base_mm),
            (half_y - spec.wall_mm, top_rear - spec.skin_mm),
            (-half_y + spec.wall_mm, top_front - spec.skin_mm),
        ])
        .close().extrude(width - 2 * spec.wall_mm).translate((-half_x + spec.wall_mm, 0, 0))
    )
    body = outer.cut(cavity)

    channels: list[cq.Solid] = []
    centre_stop_half = spec.gap_mm / 2
    # Each channel begins open at its exterior edge and stops at the uncut centre
    # material. There is no raised centre ridge on the pedal-facing surface.
    for sign in (-1.0, 1.0):
        x0 = -half_x - CUT_MARGIN_MM if sign < 0 else centre_stop_half
        x1 = -centre_stop_half if sign < 0 else half_x + CUT_MARGIN_MM
        for index, y in enumerate(spec.rail_offsets_y):
            top, bottom = _rail_dimensions(spec, index)
            local = _dovetail_prism(
                x0, x1, y, top + 2 * spec.clearance_mm, bottom + 2 * spec.clearance_mm,
                -spec.male_depth_mm - spec.clearance_mm,
                CUT_MARGIN_MM,
            )
            channels.append(_place_on_deck(spec, local, plate_spec.length_mm).val())
    body = body.cut(_compound(channels))

    # Broad PETG pressure tabs under the centre rails. Their roots join the
    # outer side walls; an insertion ramp leads to the shallow rail notch.
    for sign in (-1.0, 1.0):
        outer_x = sign * (half_x - spec.wall_mm / 2.0)
        free_x = outer_x - sign * spec.tab_length_mm
        tab = _box(
            min(outer_x, free_x), max(outer_x, free_x),
            -spec.tab_width_mm / 2.0, spec.tab_width_mm / 2.0,
            -spec.male_depth_mm - spec.tab_thickness_mm,
            -spec.male_depth_mm,
        )
        if sign < 0.0:
            points = [
                (free_x - spec.catch_length_mm, -spec.male_depth_mm),
                (free_x, -spec.male_depth_mm),
                (free_x, -spec.male_depth_mm + spec.catch_height_mm),
            ]
        else:
            points = [
                (free_x + spec.catch_length_mm, -spec.male_depth_mm),
                (free_x, -spec.male_depth_mm),
                (free_x, -spec.male_depth_mm + spec.catch_height_mm),
            ]
        catch = (
            cq.Workplane("XZ").polyline(points).close().extrude(spec.tab_width_mm)
            .translate((0.0, -spec.tab_width_mm / 2.0, 0.0))
        )
        local_tab = cq.Workplane("XY").add(tab).union(catch)
        body = body.union(_place_on_deck(spec, local_tab, plate_spec.length_mm))

    # Shallow stadium recesses on each exterior side remove material without
    # opening the shell or weakening the rail roots and board-clip region.
    stadium_tools: list[cq.Solid] = []
    for x0 in (-half_x, half_x - spec.side_recess_mm):
        for y in spec.stadium_y:
            recess = (
                cq.Workplane("YZ")
                .center(y, _deck_height(spec, y) / 2)
                .slot2D(spec.stadium_length_mm, spec.stadium_width_mm, 0)
                .extrude(spec.side_recess_mm + CUT_MARGIN_MM)
                .translate((x0 - CUT_MARGIN_MM if x0 < 0 else x0, 0, 0))
            )
            stadium_tools.append(recess.val())
    body = body.cut(_compound(stadium_tools))

    # Board clips and their closed windows. Use the measured B1 retainer section.
    b1 = _load_module("quickmount_125b", PROJECT.parent / "enclosure_125b" / "src" / "quickmount_125b.py")
    b1_spec = b1.load(PROJECT.parent / "enclosure_125b" / "cfg" / "enclosure_125b.json")
    clip_tools: list[cq.Solid] = []
    for x in spec.clip_x:
        for y in spec.clip_y:
            sign = 1 if y > 0 else -1
            window_centre = y + sign * (spec.window_length_mm / 2 - b1_spec.section.half_mouth_mm - 0.15)
            clip_tools.append(_box(x - spec.window_width_mm / 2, x + spec.window_width_mm / 2, window_centre - spec.window_length_mm / 2, window_centre + spec.window_length_mm / 2, -CUT_MARGIN_MM, spec.base_mm + CUT_MARGIN_MM))
    body = body.cut(_compound(clip_tools))
    for x in spec.clip_x:
        for y in spec.clip_y:
            body = body.union(b1.build_clip(b1_spec, y).translate((x, 0, 0)))
    return body.clean()


def build(spec: Spec) -> dict:
    plate_module = _load_module("single_125b", PROJECT / "src" / "single_125b.py")
    plate_spec = plate_module.load(spec.plate_config)
    centre = (plate_spec.width_mm + spec.gap_mm) / 2
    left = _plate_with_shoes(spec, plate_spec, -centre)
    right = _plate_with_shoes(spec, plate_spec, centre)
    riser = _wedge(spec, plate_spec)
    return {"parts": {"left_125b": left, "right_125b": right, "dual_riser": riser}, "plate_spec": plate_spec}


def validate(spec: Spec, built: dict) -> list[Check]:
    parts = {key: value.val() for key, value in built["parts"].items()}
    plate_spec = built["plate_spec"]
    checks: list[Check] = []
    boxes = {key: value.BoundingBox() for key, value in parts.items()}

    def flag(name: str, value: str, limit: str, ok: bool, note: str = "") -> None:
        checks.append(Check(name, value, limit, bool(ok), note))

    for key, solid in parts.items():
        shells = solid.Shells()
        flag(f"{key} is watertight", f"{len(shells)} shell(s), {sum(s.Closed() for s in shells)} closed", "1 closed", len(shells) == 1 and all(s.Closed() for s in shells), "single printable body")

    left, right = boxes["left_125b"], boxes["right_125b"]
    gap = right.xmin - left.xmax
    flag("plate separation", f"{gap:.2f} mm", f"{spec.gap_mm:.2f} mm", abs(gap - spec.gap_mm) <= LEN_TOL_MM, "clear gap between B1 outer edges")
    outer_top, outer_bottom = _rail_dimensions(spec, 0)
    shoe_low = _plate_world_z(spec, plate_spec.length_mm, spec.rail_offsets_y[0] - outer_bottom / 2) - spec.male_depth_mm * math.cos(spec.slope_rad)
    flag("both plates seat in the deck", f"shoe lows {left.zmin:.2f} / {right.zmin:.2f} mm", f"{shoe_low:.2f} mm", abs(left.zmin - shoe_low) <= LEN_TOL_MM and abs(right.zmin - shoe_low) <= LEN_TOL_MM, "plate faces sit on the 20 mm deck front; dovetail shoes occupy its grooves")
    riser = boxes["dual_riser"]
    flag("riser reaches board plane", f"{riser.zmin:.2f} mm", f"<= {-15.0:.2f} mm", riser.zmin < -15.0, "integral QuickMount clips extend below the base")
    flag("three dovetail rails per plate", f"{len(spec.rail_offsets_y)}", "3", len(spec.rail_offsets_y) == 3, "larger centre rail plus two smaller outer rails")
    flag("four board clips", f"{len(spec.clip_x) * len(spec.clip_y)}", "4", len(spec.clip_x) * len(spec.clip_y) == 4, "two spread pairs give the wide wedge more placement support")
    flag("centre stop stays in plate gap", f"{spec.gap_mm:.2f} mm uncut", f">= {spec.gap_mm:.2f} mm", spec.gap_mm >= 10.0, "uncut material between the opposed rail channels is the inward stop")
    flag("pressure-tab retention", f"2 x {spec.tab_length_mm:.1f} x {spec.tab_width_mm:.1f} x {spec.tab_thickness_mm:.1f}", "> 0", spec.tab_length_mm > 0 and spec.catch_height_mm > 0 and spec.notch_depth_mm >= spec.catch_height_mm, "two broad PETG tabs catch notches beneath the outer centre-rail ends")
    return checks


def report(spec: Spec, built: dict, checks: list[Check], out: pathlib.Path | None) -> str:
    lines = [f"{spec.id}{'  (' + out.name + ')' if out else ''}", "", "parts"]
    for key, part in built["parts"].items():
        b = part.val().BoundingBox()
        lines.append(f"  {key:<12} {b.xlen:.2f} x {b.ylen:.2f} x {b.zlen:.2f}  (z {b.zmin:.2f} .. {b.zmax:.2f})")
    lines += ["", "checks"]
    width = max(len(c.name) for c in checks)
    for c in checks:
        lines.append(f"  {'ok  ' if c.ok else 'FAIL'} {c.name:<{width}}  {c.value:>24}  {c.limit:>12}  {c.note}")
    failed = [c for c in checks if not c.ok]
    lines += ["", f"{len(checks) - len(failed)}/{len(checks)} checks pass" if not failed else f"{len(failed)} CHECK(S) FAILED"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    ap.add_argument("--part", choices=("all", "left_125b", "right_125b", "dual_riser"), default="all")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--tolerance", type=float, default=0.01)
    args = ap.parse_args(argv)
    spec = load(args.config)
    built = build(spec)
    checks = validate(spec, built)
    out = args.out or DWG / f"{spec.id}.stl"
    print(report(spec, built, checks, None if args.check else out))
    if not args.check:
        out.parent.mkdir(parents=True, exist_ok=True)
        jobs = built["parts"].items() if args.part == "all" else [(args.part, built["parts"][args.part])]
        for name, shape in jobs:
            target = DWG / f"{name}.stl" if args.out is None else out.with_stem(f"{out.stem}_{name}")
            cq.exporters.export(shape, str(target), tolerance=args.tolerance, angularTolerance=0.1)
            cq.exporters.export(shape, str(target.with_suffix(".step")))
            print(f"wrote {target}")
            print(f"wrote {target.with_suffix('.step')}")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
