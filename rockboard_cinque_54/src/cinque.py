"""RockBoard Cinque 5.4 as CADQuery geometry.

The board is the substrate every QuickMount plate has to sit on, so it comes out
of here in two forms:

    board      the whole thing - slotted top sheet, folded front wall, deep rear
               wall, two wedge end caps, three cross braces and the rubber feet
    top-plate  only the 3 mm top sheet, with the full mount slot pattern

Everything is read from ``cfg/rockboard_cinque_54.json``; no dimension lives in
this file.

Datum (the config's ``datum`` block): origin at the centre of the mounting field
on the top face, +X along the board length, +Y across the depth toward the
91.5 mm rear wall, +Z away from the board. The plate therefore occupies
z = -sheet .. 0, and every mount can be modelled on the z = 0 plane.

    python src/cinque.py                          # both parts, STEP + STL into dwg/
    python src/cinque.py --part top-plate --format step
    python src/cinque.py --check                  # report the derived slot field
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
from dataclasses import dataclass

import cadquery as cq

PROJECT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = PROJECT / "cfg" / "rockboard_cinque_54.json"
DWG = PROJECT / "dwg"


@dataclass(frozen=True)
class Slots:
    width: float
    rib: float
    pitch: float
    short: float
    long: float
    end_radius: float
    in_column_pitch: float
    short_only_count: int
    long_first_short_count: int

    @property
    def gap(self) -> float:
        return self.in_column_pitch - self.short


@dataclass(frozen=True)
class Field:
    length: float
    depth: float
    margin: float


@dataclass(frozen=True)
class Braces:
    count: int
    pitch: float
    width: float
    screw_dia: float


@dataclass(frozen=True)
class Feet:
    along_length: int
    across_depth: int
    dia: float
    height: float


@dataclass(frozen=True)
class Body:
    front: float
    rear: float
    angle: float
    rear_thickness: float
    rear_flange: float
    carry_width: float
    carry_height: float
    carry_below_top: float
    carry_end_offset: float
    port_dia: float
    port_below_top: float
    port_from_rear: float
    hole_dia: float
    hole_pitch: float
    hole_below_top: float
    hole_from_rear: float


@dataclass(frozen=True)
class Board:
    width: float
    depth: float
    sheet: float
    powder: float
    slots: Slots
    field: Field
    braces: Braces
    body: Body
    feet: Feet


@dataclass(frozen=True)
class Slot:
    """One slot, centre and length, in the plate plane."""

    x: float
    y: float
    length: float


def load(path: pathlib.Path = CONFIG) -> Board:
    raw = json.loads(path.read_text(encoding="utf-8"))
    slots = raw["slots"]
    types = slots["column_types"]
    body = raw["body"]
    return Board(
        width=float(raw["envelope"]["width_mm"]),
        depth=float(raw["envelope"]["depth_mm"]),
        sheet=float(raw["sheets"]["aluminium_mm"]),
        powder=float(raw["sheets"]["powder_coat_mm"]),
        slots=Slots(
            width=float(slots["width_mm"]),
            rib=float(slots["rib_mm"]),
            pitch=float(slots["pitch_mm"]),
            short=float(slots["length_families_mm"][0]),
            long=float(slots["length_families_mm"][1]),
            end_radius=float(slots["end_radius_mm"]),
            in_column_pitch=float(slots["in_column_pitch_mm"]),
            short_only_count=int(types["short_only"]["short"]),
            long_first_short_count=int(types["long_then_short"]["short"]),
        ),
        field=Field(
            length=float(raw["field"]["length_mm"]),
            depth=float(raw["field"]["depth_mm"]),
            margin=float(raw["field"]["edge_margin_mm"]),
        ),
        braces=Braces(
            count=int(raw["sheets"]["brace_count"]),
            pitch=float(raw["sheets"]["brace_spacing_mm"]),
            width=float(raw["sheets"]["brace_width_mm"]),
            screw_dia=float(raw["sheets"]["brace_screw_dia_mm"]),
        ),
        body=Body(
            front=float(body["front_wall_mm"]),
            rear=float(body["rear_wall_mm"]),
            angle=float(body["underside_angle_deg"]),
            rear_thickness=float(body["rear_wall_thickness_mm"]),
            rear_flange=float(body["rear_flange_mm"]),
            carry_width=float(body["carry_opening"]["width_mm"]),
            carry_height=float(body["carry_opening"]["height_mm"]),
            carry_below_top=float(body["carry_opening"]["below_top_mm"]),
            carry_end_offset=float(body["carry_opening"]["end_offset_mm"]),
            port_dia=float(body["end_port"]["dia_mm"]),
            port_below_top=float(body["end_port"]["below_top_mm"]),
            port_from_rear=float(body["end_port"]["from_rear_mm"]),
            hole_dia=float(body["end_holes"]["dia_mm"]),
            hole_pitch=float(body["end_holes"]["pitch_mm"]),
            hole_below_top=float(body["end_holes"]["below_top_mm"]),
            hole_from_rear=float(body["end_holes"]["from_rear_mm"]),
        ),
        feet=Feet(
            along_length=int(body["feet"]["along_length"]),
            across_depth=int(body["feet"]["across_depth"]),
            dia=float(body["feet"]["dia_mm"]),
            height=float(body["feet"]["height_mm"]),
        ),
    )


def column_count(board: Board) -> int:
    """How many slot columns the annotated grid fits across the field depth."""
    usable = board.field.depth - board.slots.width
    return int(math.floor(usable / board.slots.pitch + 1e-9)) + 1


def column_centres(board: Board) -> list[float]:
    """Slot column centres in Y, symmetric about the board centre line."""
    count = column_count(board)
    span = (count - 1) * board.slots.pitch + board.slots.width
    first = -span / 2 + board.slots.width / 2
    return [first + index * board.slots.pitch for index in range(count)]


def slot_layout(board: Board) -> list[Slot]:
    """Every slot on the plate.

    Columns alternate: the even ones start with one 98 mm slot and then run
    60 mm slots a half pitch behind their neighbours, which is the stagger the
    drawing shows. Odd columns are 60 mm slots only and fill the field exactly.
    """
    slots = board.slots
    end = board.field.length / 2
    layout: list[Slot] = []
    for index, y in enumerate(column_centres(board)):
        cursor = -end
        if index % 2 == 0:
            layout.append(Slot(cursor + slots.long / 2, y, slots.long))
            cursor += slots.long + slots.gap
            count = slots.long_first_short_count
        else:
            count = slots.short_only_count
        for _ in range(count):
            layout.append(Slot(cursor + slots.short / 2, y, slots.short))
            cursor += slots.in_column_pitch
    return layout


def check(board: Board) -> list[str]:
    """Reasons the configured grid cannot be built, empty when it can."""
    problems: list[str] = []
    slots, field = board.slots, board.field
    count = column_count(board)
    span = (count - 1) * slots.pitch + slots.width
    if span > field.depth + 1e-6:
        problems.append(
            f"{count} columns span {span:.2f} mm across a {field.depth:.2f} mm field"
        )
    if abs(slots.pitch - (slots.width + slots.rib)) > 1e-6:
        problems.append(
            f"pitch {slots.pitch} mm is not slot {slots.width} + rib {slots.rib}"
        )
    if abs(slots.in_column_pitch - (slots.short + slots.gap)) > 1e-6:
        problems.append(
            f"in-column pitch {slots.in_column_pitch} is not slot + gap "
            f"{slots.short} + {slots.gap}"
        )
    short_column = (
        slots.short_only_count * slots.short
        + (slots.short_only_count - 1) * slots.gap
    )
    if abs(short_column - field.length) > 1e-6:
        problems.append(
            f"a short column fills {short_column:.2f} mm of a {field.length:.2f} mm field"
        )
    long_column_end = (
        slots.long
        + slots.gap
        + slots.long_first_short_count * slots.in_column_pitch
        - slots.gap
    )
    if long_column_end > field.length + 1e-6:
        problems.append(
            f"a long-first column runs {long_column_end:.2f} mm past a "
            f"{field.length:.2f} mm field"
        )
    if board.depth - 2 * field.margin != field.depth:
        problems.append("field depth does not match the board depth and its margin")
    underside = math.degrees(
        math.atan2(board.body.rear - board.body.front, board.depth)
    )
    if abs(underside - board.body.angle) > 0.05:
        problems.append(
            f"underside angle {underside:.2f} deg does not match the "
            f"configured {board.body.angle} deg"
        )
    return problems


def _rounded_slot(board: Board, length: float) -> cq.Solid:
    height = board.sheet + 1.0
    return (
        cq.Workplane("XY")
        .rect(length, board.slots.width)
        .extrude(height)
        .edges("|Z")
        .fillet(board.slots.end_radius)
        .val()
    )


def build_top_plate(board: Board) -> cq.Workplane:
    """The 3 mm slotted sheet, on its own."""
    plate = (
        cq.Workplane("XY")
        .box(board.width, board.depth, board.sheet, centered=(True, True, True))
        .translate((0, 0, -board.sheet / 2))
    )
    cutters = {
        length: _rounded_slot(board, length)
        for length in (board.slots.short, board.slots.long)
    }
    tools = [
        cutters[slot.length].translate(cq.Vector(slot.x, slot.y, -board.sheet - 0.5))
        for slot in slot_layout(board)
    ]
    return plate.cut(cq.Workplane(obj=cq.Compound.makeCompound(tools)))


def _wedge_profile(board: Board) -> cq.Workplane:
    """End-cap outline in YZ: flat top, vertical walls, 9 degree underside."""
    half = board.depth / 2
    return (
        cq.Workplane("YZ")
        .polyline(
            [
                (-half, 0.0),
                (half, 0.0),
                (half, -board.body.rear),
                (-half, -board.body.front),
            ]
        )
        .close()
    )


def _underside_z(board: Board, y: float) -> float:
    """Height of the sloping underside at depth y."""
    rise = board.body.rear - board.body.front
    return -board.body.front - (y + board.depth / 2) * rise / board.depth


def build_body(board: Board) -> cq.Workplane:
    """Front wall, rear wall, both end caps and the three cross braces."""
    half_length = board.width / 2
    half_depth = board.depth / 2
    wall = board.sheet

    front = (
        cq.Workplane("XY")
        .box(board.width, wall, board.body.front, centered=(True, True, False))
        .translate((0, -half_depth + wall / 2, -board.body.front))
    )
    rear = (
        cq.Workplane("XY")
        .box(
            board.width,
            board.body.rear_thickness,
            board.body.rear,
            centered=(True, True, False),
        )
        .translate(
            (0, half_depth - board.body.rear_thickness / 2, -board.body.rear)
        )
    )

    caps = cq.Workplane("XY")
    for direction in (-1.0, 1.0):
        cap = (
            _wedge_profile(board)
            .extrude(wall)
            .translate((direction * half_length - (wall if direction > 0 else 0), 0, 0))
        )
        caps = caps.union(cap)

    shell = front.union(rear).union(caps)

    # Carried as one opening per wall end, 24 mm under the top.
    opening_z = -board.body.carry_below_top - board.body.carry_height / 2
    for direction in (-1.0, 1.0):
        cut = (
            cq.Workplane("XY")
            .box(
                board.body.carry_width,
                board.body.rear_thickness * 4,
                board.body.carry_height,
                centered=(True, True, True),
            )
            .translate(
                (
                    direction * (half_length - board.body.carry_end_offset)
                    - direction * board.body.carry_width / 2,
                    half_depth - board.body.rear_thickness / 2,
                    opening_z,
                )
            )
        )
        shell = shell.cut(cut)

    # End-cap details: one cable port and a pair of fixing holes, axis along X.
    for direction in (-1.0, 1.0):
        cap_x = direction * half_length
        wall_y = half_depth - board.body.port_from_rear
        port = (
            cq.Workplane("YZ")
            .center(wall_y, -board.body.port_below_top)
            .circle(board.body.port_dia / 2)
            .extrude(wall * 4)
            .translate((cap_x - wall * 2, 0, 0))
        )
        shell = shell.cut(port)
        hole_y = half_depth - board.body.hole_from_rear
        for index in range(2):
            hole = (
                cq.Workplane("YZ")
                .center(
                    hole_y, -board.body.hole_below_top - index * board.body.hole_pitch
                )
                .circle(board.body.hole_dia / 2)
                .extrude(wall * 4)
                .translate((cap_x - wall * 2, 0, 0))
            )
            shell = shell.cut(hole)

    return shell.union(_braces(board))


def _braces(board: Board) -> cq.Workplane:
    """Three cross braces: a 52 mm top flange with a sloping web under it."""
    half_depth = board.depth / 2
    wall = board.sheet
    brace = cq.Workplane("XY")
    spans = [0.0]
    for index in range(1, board.braces.count // 2 + 1):
        spans.extend((-index * board.braces.pitch, index * board.braces.pitch))
    spans = sorted(spans[: board.braces.count])

    for x in spans:
        flange = (
            cq.Workplane("XY")
            .box(board.braces.width, board.depth, wall, centered=(True, True, False))
            .translate((x, 0, -wall * 2))
        )
        web_profile = (
            cq.Workplane("YZ")
            .polyline(
                [
                    (-half_depth + wall, -wall * 2),
                    (half_depth - board.body.rear_thickness, -wall * 2),
                    (
                        half_depth - board.body.rear_thickness,
                        _underside_z(board, half_depth - board.body.rear_thickness),
                    ),
                    (-half_depth + wall, _underside_z(board, -half_depth + wall)),
                ]
            )
            .close()
        )
        web = web_profile.extrude(wall).translate((x - wall / 2, 0, 0))
        brace = brace.union(flange).union(web)
    return brace


def _feet(board: Board) -> cq.Workplane:
    """Rubber pads under the front and rear wall bottom edges."""
    pads = cq.Workplane("XY")
    inset = board.width / 2 - board.feet.dia
    steps = max(board.feet.along_length - 1, 1)
    xs = [-inset + 2 * inset * index / steps for index in range(steps + 1)]
    half_depth = board.depth / 2
    rows = {
        -half_depth + board.feet.dia / 2: -board.body.front,
        half_depth - board.feet.dia / 2: -board.body.rear,
    }
    for y, z in rows.items():
        for x in xs:
            pad = (
                cq.Workplane("XY")
                .circle(board.feet.dia / 2)
                .extrude(board.feet.height)
                .translate((x, y, z - board.feet.height))
            )
            pads = pads.union(pad)
    return pads


def build_board(board: Board) -> cq.Workplane:
    """The complete board."""
    return build_top_plate(board).union(build_body(board)).union(_feet(board))


def export(shape: cq.Workplane, stem: str, formats: str, out: pathlib.Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    wanted = ("step", "stl") if formats == "both" else (formats,)
    for fmt in wanted:
        path = out / f"{stem}.{fmt}"
        cq.exporters.export(shape, str(path))
        print(f"wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--part",
        choices=("board", "top-plate", "all"),
        default="all",
        help="which geometry to build (default: all)",
    )
    parser.add_argument(
        "--format",
        choices=("step", "stl", "both"),
        default="both",
        help="output format (default: both)",
    )
    parser.add_argument("--out", type=pathlib.Path, default=DWG, help="output folder")
    parser.add_argument(
        "--check",
        action="store_true",
        help="print the derived slot field and exit without building",
    )
    args = parser.parse_args()

    board = load()
    problems = check(board)
    for problem in problems:
        print(f"config error: {problem}")
    if problems:
        raise SystemExit(1)

    if args.check:
        layout = slot_layout(board)
        print(f"board        {board.width} x {board.depth} mm, sheet {board.sheet} mm")
        print(f"field        {board.field.length} x {board.field.depth} mm")
        print(f"columns      {column_count(board)} at {board.slots.pitch} mm pitch")
        print(
            f"slots        {len(layout)} pieces "
            f"({sum(1 for s in layout if s.length == board.slots.long)} long)"
        )
        return

    if args.part in ("top-plate", "all"):
        export(build_top_plate(board), "cinque54_top_plate", args.format, args.out)
    if args.part in ("board", "all"):
        export(build_board(board), "cinque54_board", args.format, args.out)


if __name__ == "__main__":
    main()
