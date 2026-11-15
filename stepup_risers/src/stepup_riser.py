"""Generate a PETG step-up riser that is both a platform and a QuickMount plate.

The riser closes the gap between two Warwick products:

* the **Step Up** kits are a 1 mm bent steel shelf, 90 / 180 / 255 x 142.5 mm and
  25 mm tall, with a plain top drilled for the pedals, and no way to carry a
  QuickMount plate on it;
* the **PedalRiser** family is a wedge whose top carries the board's own slot
  field, so a QuickMount plate drops onto it, but it is 41-49 mm tall and its
  underside is a set of bent steel hooks rather than a plate.

This module prints one part that does both jobs:

* top    a 4 mm sheet with the board's slot field cut into it - 18 mm slots,
         16 mm ribs, R4 ends - so a QuickMount plated pedal drops on and its
         retainers grip the ribs exactly as they grip the board. The sheet is
         4 mm rather than the board's 3 mm because the retainer's ledge sits
         4 mm below the pedal plate's underside; a 4 mm sheet puts the ledge
         flush under it with no foam pad in between.
* base   a 3 mm plate that behaves like a pedal plate: two integral C-loops
         hang below it, so the riser itself clips to the board.
* body   a 3 mm perimeter wall with a rib grid, so the part prints as one piece.

Everything comes out of the config; no dimension lives here. The clip section is
read from ``../commons/cfg/retainer.json`` rather than restated, and the integral
clip is built the same way as the Type B1 plate's, with the post fused into the
base plate and the blade standing in an open window.

Datum (each config's ``datum`` block): origin at the centre of the base
footprint on the board-facing face. +X across the length, +Y across the depth,
+Z up toward the pedals. The base plate occupies z = 0..3, the body z = 3..21,
the slotted top sheet z = 21..25 and the clips z < 0.

    .venv/Scripts/python stepup_risers/src/stepup_riser.py --list
    .venv/Scripts/python stepup_risers/src/stepup_riser.py --config riser_two_125b
    .venv/Scripts/python stepup_risers/src/stepup_riser.py --config riser_two_125b --check
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
from dataclasses import dataclass

import cadquery as cq

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CFG = PROJECT / "cfg"
DWG = PROJECT / "dwg"

# Slack for booleans only: big enough to clear a face, small enough not to change
# what a cut selects. Never a part dimension.
CUT_MARGIN_MM = 1.0


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ClipSection:
    """The shared retainer section, read from commons so it is never restated."""

    width_along_slot_mm: float
    outer_width_mm: float
    mouth_width_mm: float
    post_wall_mm: float
    blade_wall_mm: float
    blade_tip_chamfer_mm: float
    ledge_drop_mm: float
    ledge_protrusion_mm: float
    drop_below_plate_top_mm: float
    plate_thickness_mm: float

    @property
    def half_outer_mm(self) -> float:
        return self.outer_width_mm / 2.0

    @property
    def half_mouth_mm(self) -> float:
        return self.mouth_width_mm / 2.0

    @property
    def blade_outer_half_mm(self) -> float:
        return self.half_mouth_mm + self.blade_wall_mm

    @property
    def arch_wall_mm(self) -> float:
        return self.half_outer_mm - self.half_mouth_mm

    @property
    def loop_drop_mm(self) -> float:
        return self.drop_below_plate_top_mm - self.plate_thickness_mm

    @property
    def arch_centre_z_mm(self) -> float:
        return -(self.loop_drop_mm - self.half_outer_mm)

    @property
    def ledge_z_mm(self) -> float:
        return -self.ledge_drop_mm

    @property
    def tip_z_mm(self) -> float:
        return self.plate_thickness_mm


@dataclass(frozen=True)
class SlotField:
    """The slot field cut into the top sheet, and the ribs it leaves standing."""

    slot_width_mm: float
    rib_width_mm: float
    end_radius_mm: float
    slot_length_mm: float
    rib_centres_mm: list[float]
    slot_x_centres_mm: list[float]

    def slot_rows(self) -> list[float]:
        """Every slot centreline in Y, deduplicated for shared slots."""
        step = self.rib_width_mm / 2.0 + self.slot_width_mm / 2.0
        rows = sorted(
            {round(c + s * step, 3) for c in self.rib_centres_mm for s in (-1, 1)}
        )
        return rows

    def slots(self) -> list[tuple[float, float]]:
        """(x, y) centre of every slot, deduplicated."""
        return sorted(
            {(round(x, 3), y) for y in self.slot_rows() for x in self.slot_x_centres_mm}
        )


@dataclass(frozen=True)
class RiserSpec:
    raw: dict
    id: str
    length_mm: float
    depth_mm: float
    height_mm: float
    slope_deg: float
    corner_radius_mm: float
    base_thickness_mm: float
    top_thickness_mm: float
    wall_thickness_mm: float
    rib_width_mm: float
    ribs_along_x_at_y_mm: list[float]
    ribs_along_y_at_x_mm: list[float]
    field: SlotField
    section: ClipSection
    clip_centres_y_mm: list[float]
    window_width_mm: float
    window_length_mm: float
    window_radius_mm: float
    board_pitch_mm: float
    material_id: str
    density_g_cm3: float

    @property
    def slope_rad(self) -> float:
        return math.radians(self.slope_deg)

    @property
    def deck_span_mm(self) -> float:
        """The deck's length along its own slope, so its plan depth is `depth`."""
        return self.depth_mm / math.cos(self.slope_rad)

    @property
    def low_height_mm(self) -> float:
        """Deck top face at the low (front) edge: the shortest the riser gets."""
        return self.height_mm - self.depth_mm * math.tan(self.slope_rad)

    @property
    def high_height_mm(self) -> float:
        """Deck top face at the high (rear) edge: the riser's overall height."""
        return self.height_mm

    def deck_top_z(self, y_mm: float) -> float:
        """Deck top face height at depth y."""
        return self.low_height_mm + (y_mm + self.depth_mm / 2.0) * math.tan(
            self.slope_rad
        )

    def deck_under_z(self, y_mm: float) -> float:
        """Deck underside height at depth y; a slope plane's vertical offset is t/cos."""
        return self.deck_top_z(y_mm) - self.top_thickness_mm / math.cos(self.slope_rad)

    @property
    def clip_spacing_mm(self) -> float:
        return abs(self.clip_centres_y_mm[1] - self.clip_centres_y_mm[0])

    @property
    def retainer_clearance_mm(self) -> float:
        """Gap left under the lowest point of a hanging retainer, at the low edge.

        A pedal plate sits on the riser's deck, so its retainer hangs from the
        deck's top face, not from the deck's underside.
        """
        return self.low_height_mm - self.section.loop_drop_mm - self.base_thickness_mm


def _read(path: pathlib.Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing config: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _section(raw: dict, plate_thickness_mm: float) -> ClipSection:
    env, sec = raw["envelope"], raw["section"]
    ledge = sec["ledge"]
    return ClipSection(
        width_along_slot_mm=float(env["width_mm"]),
        outer_width_mm=float(env["outer_width_mm"]),
        mouth_width_mm=float(sec["mouth_width_mm"]),
        post_wall_mm=float(sec["post_wall_mm"]),
        blade_wall_mm=float(sec["blade_wall_mm"]),
        blade_tip_chamfer_mm=float(sec["blade_tip_chamfer_mm"]),
        ledge_drop_mm=float(ledge["drop_below_plate_mm"]),
        ledge_protrusion_mm=float(ledge["protrusion_mm"]),
        drop_below_plate_top_mm=float(env["drop_below_plate_top_mm"]),
        plate_thickness_mm=plate_thickness_mm,
    )


def _deck_height(
    env: dict, height: dict | None, base: float, section: ClipSection
) -> float:
    """The deck's high-edge height, so the deck's low edge sets the clearance.

    `clip_clearance` derives it: a pedal plate's retainer hangs `loop_drop` below
    the plate it belongs to, that plate rests on the deck's top face, so the least
    the low edge may stand is base + clearance + loop_drop. The slope then lifts
    the high edge by depth * tan(slope).
    """
    depth = float(env["depth_mm"])
    slope = math.radians(float(env["deck_slope_deg"]))
    if height is None:
        return float(env["height_mm"])
    mode = height.get("mode", "fixed")
    if mode == "clip_clearance":
        low = float(base) + float(height["clearance_mm"]) + section.loop_drop_mm
        return low + depth * math.tan(slope)
    if mode != "fixed":
        raise ValueError(f"unknown height mode {mode!r}")
    given = float(height["height_mm"])
    if height.get("at", "high") == "high":
        return given
    return given + depth * math.tan(slope)


def load(path: pathlib.Path) -> RiserSpec:
    raw = _read(path)
    env = raw["envelope"]
    base = raw["base"]
    body = raw["body"]
    top = raw["top"]
    field = top["slot_field"]
    clips = raw["clips"]
    material = raw["material"]

    section_raw = _read(PROJECT / clips["section"])
    base_thickness = float(base["thickness_mm"])
    section = _section(section_raw, base_thickness)
    presets = _read(PROJECT / material["presets_from"])["material"]["presets"]
    material_id = str(material["id"])
    if material_id not in presets:
        raise KeyError(f"{material['presets_from']}: no preset for {material_id!r}")

    return RiserSpec(
        raw=raw,
        id=str(raw["id"]),
        length_mm=float(env["length_mm"]),
        depth_mm=float(env["depth_mm"]),
        height_mm=_deck_height(env, raw.get("height"), base_thickness, section),
        slope_deg=float(env["deck_slope_deg"]),
        corner_radius_mm=float(env["corner_radius_mm"]),
        base_thickness_mm=base_thickness,
        top_thickness_mm=float(top["sheet_thickness_mm"]),
        wall_thickness_mm=float(body["wall_thickness_mm"]),
        rib_width_mm=float(body["rib_width_mm"]),
        ribs_along_x_at_y_mm=[float(v) for v in body["ribs_along_x_at_y_mm"]],
        ribs_along_y_at_x_mm=[float(v) for v in body["ribs_along_y_at_x_mm"]],
        field=SlotField(
            slot_width_mm=float(field["slot_width_mm"]),
            rib_width_mm=float(field["rib_width_mm"]),
            end_radius_mm=float(field["end_radius_mm"]),
            slot_length_mm=float(field["slot_length_mm"]),
            rib_centres_mm=[float(v) for v in field["rib_centres_mm"]],
            slot_x_centres_mm=[float(v) for v in field["slot_x_centres_mm"]],
        ),
        section=section,
        clip_centres_y_mm=[float(v) for v in clips["centres_y_mm"]],
        window_width_mm=float(clips["window_width_mm"]),
        window_length_mm=float(clips["window_length_mm"]),
        window_radius_mm=float(clips["window_radius_mm"]),
        board_pitch_mm=float(raw["board"]["pitch_mm"]),
        material_id=material_id,
        density_g_cm3=float(presets[material_id]["density_g_cm3"]),
    )


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #


def _plate(
    length: float, depth: float, radius: float, z0: float, z1: float
) -> cq.Workplane:
    """A rounded rectangle extruded from z0 to z1."""
    height = z1 - z0
    return (
        cq.Workplane("XY")
        .rect(length, depth)
        .extrude(height)
        .edges("|Z")
        .fillet(radius)
        .translate((0.0, 0.0, z0))
    )


def _bar(
    x0: float, x1: float, y0: float, y1: float, z0: float, z1: float
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=(True, True, True))
        .translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0))
    )


def _deck_place(spec: RiserSpec, shape: cq.Workplane) -> cq.Workplane:
    """Rotate a shape built flat in the deck's frame onto the sloped deck.

    In that frame the deck's top face is z = 0 and it spans v = -+span/2 in Y, so
    after the tilt its plan depth is `depth` and its low edge lands at
    `low_height_mm`.
    """
    shift = spec.low_height_mm + math.sin(spec.slope_rad) * spec.deck_span_mm / 2.0
    return shape.rotate((0, 0, 0), (1, 0, 0), spec.slope_deg).translate(
        (0.0, 0.0, shift)
    )


def _loop_section(section: ClipSection) -> tuple[list[tuple], list[tuple]]:
    """Outer silhouette and mouth for the integral clip, in (y, z), post at +y.

    Identical to the Type B1 plate's integral clip: both arms run the full base
    plate thickness, the post finishes inside the plate's material and fuses to
    it, and the blade stands in an open window so its tip lands flush with the
    plate's top face and stays free to flex the ledge.
    """
    xo, xm = section.half_outer_mm, section.half_mouth_mm
    xb = section.blade_outer_half_mm
    za = section.arch_centre_z_mm
    bottom = -section.loop_drop_mm
    zl = section.ledge_z_mm
    top = section.tip_z_mm
    ch = section.blade_tip_chamfer_mm

    outer = [
        ("L", xo, top),
        ("L", xo, za),
        ("A", -xo, za, 0.0, bottom),
        ("L", -xo, zl),
        ("L", -xb, zl),
        ("L", -xb, top - ch),
        ("L", -xb + ch, top),
    ]
    mouth = [
        ("L", xm, top + CUT_MARGIN_MM),
        ("L", xm, za),
        ("A", -xm, za, 0.0, bottom + section.arch_wall_mm),
        ("L", -xm, top + CUT_MARGIN_MM),
    ]
    return outer, mouth


def _extrude_loop(segments: list[tuple], width: float, mirror: bool) -> cq.Workplane:
    first = segments[0]
    sign = -1.0 if mirror else 1.0
    wp = cq.Workplane("YZ").moveTo(sign * first[1], first[2])
    for seg in segments[1:]:
        if seg[0] == "L":
            wp = wp.lineTo(sign * seg[1], seg[2])
        else:
            wp = wp.threePointArc((sign * seg[3], seg[4]), (sign * seg[1], seg[2]))
    wp = wp.close().extrude(width)
    box = wp.val().BoundingBox()
    return wp.translate((-(box.xmin + box.xmax) / 2.0, 0.0, 0.0))


def build_clip(spec: RiserSpec, centre_y_mm: float) -> cq.Workplane:
    """One integral C-loop at `centre_y_mm`; the blade - and its ledge - point outboard."""
    outer, mouth = _loop_section(spec.section)
    mirror = centre_y_mm > 0.0
    body = _extrude_loop(outer, spec.section.width_along_slot_mm, mirror)
    void = _extrude_loop(
        mouth, spec.section.width_along_slot_mm + CUT_MARGIN_MM * 2.0, mirror
    )
    return body.cut(void).translate((0.0, centre_y_mm, 0.0))


def _window_centre_y(spec: RiserSpec, clip_y: float) -> float:
    """Centre of the closed window that frees the blade, measured from the clip centre.

    The Type B1 window opens to the plate edge; here the clip sits inside the
    footprint, so the same opening is closed off outboard. Its inboard wall lands
    on the clip's mouth wall, exactly as it does on the B1 plate.
    """
    sign = 1.0 if clip_y > 0 else -1.0
    return clip_y + sign * (
        spec.window_length_mm / 2.0 - spec.section.half_mouth_mm - 0.15
    )


def build_base(spec: RiserSpec) -> cq.Workplane:
    plate = _plate(
        spec.length_mm,
        spec.depth_mm,
        spec.corner_radius_mm,
        0.0,
        spec.base_thickness_mm,
    )
    windows: list[cq.Workplane] = []
    for clip_y in spec.clip_centres_y_mm:
        window = _plate(
            spec.window_width_mm,
            spec.window_length_mm,
            spec.window_radius_mm,
            -CUT_MARGIN_MM,
            spec.base_thickness_mm + CUT_MARGIN_MM,
        ).translate((0.0, _window_centre_y(spec, clip_y), 0.0))
        windows.append(window)
    return plate.cut(
        cq.Workplane(obj=cq.Compound.makeCompound([w.val() for w in windows]))
    )


def build_body(spec: RiserSpec) -> cq.Workplane:
    """Perimeter wall and ribs under a sloped deck: the step-up's own silhouette.

    The body is the solid between the base plate and the deck's underside. The
    deck's underside is a plane, so the whole body is one prism with a sloped top,
    dug out to a 3 mm perimeter and filled with ribs. Cutting the cavity from that
    prism (rather than from a box) is what gives the part the wedge profile a Step
    Up has, instead of four vertical walls of one height.
    """
    wall = spec.wall_thickness_mm
    half_x = spec.length_mm / 2.0
    half_y = spec.depth_mm / 2.0
    lip = CUT_MARGIN_MM * 0.3

    def prism(y0: float, y1: float, z0: float, lift: float) -> cq.Workplane:
        pts = [
            (y0, z0),
            (y1, z0),
            (y1, spec.deck_under_z(y1) + lift),
            (y0, spec.deck_under_z(y0) + lift),
        ]
        return (
            cq.Workplane("YZ")
            .polyline(pts)
            .close()
            .extrude(spec.length_mm)
            .translate((-half_x, 0.0, 0.0))
        )

    tall = spec.high_height_mm + CUT_MARGIN_MM
    outline = _plate(spec.length_mm, spec.depth_mm, spec.corner_radius_mm, 0.0, tall)
    outer = prism(-half_y, half_y, 0.0, lip).intersect(outline)
    void = prism(-half_y + wall, half_y - wall, wall, 0.0).intersect(
        _plate(
            spec.length_mm - 2.0 * wall,
            spec.depth_mm - 2.0 * wall,
            max(spec.corner_radius_mm - wall, 0.5),
            0.0,
            tall,
        )
    )
    shell = outer.cut(void)

    half_rib = spec.rib_width_mm / 2.0
    ribs = cq.Workplane("XY")
    for y in spec.ribs_along_x_at_y_mm:
        ribs = ribs.union(
            _bar(
                -half_x,
                half_x,
                y - half_rib,
                y + half_rib,
                spec.base_thickness_mm,
                tall,
            )
        )
    for x in spec.ribs_along_y_at_x_mm:
        ribs = ribs.union(
            _bar(
                x - half_rib,
                x + half_rib,
                -half_y,
                half_y,
                spec.base_thickness_mm,
                tall,
            )
        )
    return shell.union(ribs.intersect(outer))


def retainer_keep_outs(spec: RiserSpec) -> list[cq.Solid]:
    """Volumes a hanging retainer needs below the deck, one per slot pair.

    A retainer drops through the two slots either side of one rib; its loop is
    `outer_width` across the rib and as long as the slot. Measured from the deck's
    underside, which is where the plate that carries it beds, down to the loop's
    lowest point. It stops at that underside so the deck itself stays whole - the
    slot, not this box, is what the retainer passes through. Built in the deck's own
    frame so it stays square to a sloped deck.
    """
    section = spec.section
    cos = math.cos(spec.slope_rad)
    half_clear = section.outer_width_mm / 2.0 + 0.5
    z0 = -section.loop_drop_mm - 0.5
    z1 = -spec.top_thickness_mm
    half_len = spec.field.slot_length_mm / 2.0

    boxes: list[cq.Solid] = []
    for rib_y in spec.field.rib_centres_mm:
        v = rib_y / cos
        for x in spec.field.slot_x_centres_mm:
            local = _bar(
                x - half_len, x + half_len, v - half_clear, v + half_clear, z0, z1
            )
            boxes.append(_deck_place(spec, local).val())
    return boxes


def build_top(spec: RiserSpec) -> cq.Workplane:
    """The sloped deck: the board's slot field cut square to the deck's own plane."""
    field = spec.field
    thickness = spec.top_thickness_mm
    cos = math.cos(spec.slope_rad)
    sheet = _plate(
        spec.length_mm, spec.deck_span_mm, spec.corner_radius_mm, -thickness, 0.0
    )
    cutters = [
        _plate(
            field.slot_length_mm,
            field.slot_width_mm,
            field.end_radius_mm,
            -thickness - CUT_MARGIN_MM,
            CUT_MARGIN_MM,
        ).translate((x, y / cos, 0.0))
        for x, y in field.slots()
    ]
    sheet = sheet.cut(
        cq.Workplane(obj=cq.Compound.makeCompound([c.val() for c in cutters]))
    )
    sheet = _deck_place(spec, sheet)
    # A tilted plate is wider in plan than it is thick, so trim it back to the
    # footprint: that leaves a vertical front lip and side edges, as a bent Step Up
    # has, instead of a plate overhanging its own base.
    return sheet.intersect(
        _plate(
            spec.length_mm,
            spec.depth_mm,
            spec.corner_radius_mm,
            -CUT_MARGIN_MM,
            spec.high_height_mm + CUT_MARGIN_MM,
        )
    )


def build(spec: RiserSpec) -> cq.Workplane:
    part = build_base(spec)
    part = part.union(build_body(spec))
    part = part.union(build_top(spec))
    for clip_y in spec.clip_centres_y_mm:
        part = part.union(build_clip(spec, clip_y))
    part = _cut(part, retainer_keep_outs(spec))
    return part.clean()


def _cut(shape: cq.Workplane, tools: list[cq.Solid]) -> cq.Workplane:
    if not tools:
        return shape
    return shape.cut(cq.Workplane(obj=cq.Compound.makeCompound(tools)))


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


def validate(spec: RiserSpec, part: cq.Workplane) -> list[Check]:
    checks: list[Check] = []
    section = spec.section
    field = spec.field

    box = part.val().BoundingBox()
    checks.append(
        Check(
            "envelope length",
            f"{box.xlen:.2f}",
            f"{spec.length_mm:.2f}",
            abs(box.xlen - spec.length_mm) < 0.1,
        )
    )
    checks.append(
        Check(
            "envelope depth",
            f"{box.ylen:.2f}",
            f"{spec.depth_mm:.2f}",
            abs(box.ylen - spec.depth_mm) < 0.1,
        )
    )
    overview = spec.high_height_mm + section.loop_drop_mm
    checks.append(
        Check(
            "envelope height (high edge to clip bottom)",
            f"{box.zlen:.2f}",
            f"{overview:.2f}",
            abs(box.zlen - overview) < 0.2,
            "clips hang below the base plate, so the part is taller than the riser",
        )
    )
    checks.append(
        Check(
            "deck falls from high to low edge",
            f"{spec.high_height_mm:.2f} -> {spec.low_height_mm:.2f} at "
            f"{spec.slope_deg:.2f} deg",
            "slope > 0",
            spec.slope_deg > 0.0,
            f"over {spec.depth_mm:.1f} of depth, so {spec.deck_span_mm:.2f} along the deck",
        )
    )

    checks.append(
        Check(
            "slot width clears its end radius",
            f"{field.slot_width_mm:.2f}",
            f"> {2 * field.end_radius_mm:.2f}",
            field.slot_width_mm > 2 * field.end_radius_mm,
        )
    )
    checks.append(
        Check(
            "rib width against the retainer mouth",
            f"{field.rib_width_mm:.2f} rib / {section.mouth_width_mm:.2f} mouth",
            "rib > mouth (interference fit)",
            field.rib_width_mm > section.mouth_width_mm,
            f"{field.rib_width_mm - section.mouth_width_mm:.2f} mm squeeze, "
            f"{(field.rib_width_mm - section.mouth_width_mm) / 2:.2f} a side",
        )
    )
    checks.append(
        Check(
            "top sheet thickness against the ledge drop",
            f"{spec.top_thickness_mm:.2f} sheet / {section.ledge_drop_mm:.2f} ledge",
            "equal, for a flush grip",
            abs(spec.top_thickness_mm - section.ledge_drop_mm) < 0.01,
            "a thinner sheet needs the board's 1 mm foam pad under the plate",
        )
    )
    checks.append(
        Check(
            "retainer clears the base plate",
            f"{spec.retainer_clearance_mm:.2f} clear",
            "> 0",
            spec.retainer_clearance_mm > 0.0,
            "clear height under a hanging retainer",
        )
    )

    multiple = spec.clip_spacing_mm / spec.board_pitch_mm
    checks.append(
        Check(
            "clip pair on the board pitch",
            f"{spec.clip_spacing_mm:.2f} = {multiple:.3f} x {spec.board_pitch_mm:.2f}",
            "whole number of pitches",
            abs(multiple - round(multiple)) < 0.02,
        )
    )

    half_outer = section.outer_width_mm / 2.0
    clip_margin = min(
        spec.depth_mm / 2.0 - abs(y) - half_outer for y in spec.clip_centres_y_mm
    )
    checks.append(
        Check(
            "clip loop inside the footprint",
            f"{clip_margin:.2f} to the edge",
            "> 0",
            clip_margin > 0.0,
        )
    )
    window_margin = min(
        spec.depth_mm / 2.0
        - abs(_window_centre_y(spec, y))
        - spec.window_length_mm / 2.0
        for y in spec.clip_centres_y_mm
    )
    checks.append(
        Check(
            "clip window inside the footprint",
            f"{window_margin:.2f} to the edge",
            "> 0",
            window_margin > 0.0,
            "the window is the closed version of the B1 end window",
        )
    )

    slot_edge = max(abs(y) + field.slot_width_mm / 2.0 for y in field.slot_rows())
    checks.append(
        Check(
            "slot field inside the footprint",
            f"{slot_edge:.2f}",
            f"< {spec.depth_mm / 2.0 - spec.wall_thickness_mm:.2f} inner wall",
            slot_edge < spec.depth_mm / 2.0 - spec.wall_thickness_mm,
        )
    )

    keep_out_spread = (section.outer_width_mm / 2.0 + 0.5) * math.cos(
        spec.slope_rad
    ) + section.loop_drop_mm * math.sin(spec.slope_rad)
    keep_out_edge = max(abs(y) + keep_out_spread for y in field.rib_centres_mm)
    checks.append(
        Check(
            "retainer keep-out inside the inner wall",
            f"{keep_out_edge:.2f}",
            f"< {spec.depth_mm / 2.0 - spec.wall_thickness_mm:.2f}",
            keep_out_edge < spec.depth_mm / 2.0 - spec.wall_thickness_mm,
            "the keep-out is square to the deck, so the slope adds to its Y spread; "
            "one that reaches the wall cuts the wall away",
        )
    )

    volume_cm3 = part.val().Volume() / 1000.0
    mass = volume_cm3 * spec.density_g_cm3
    checks.append(
        Check(
            "solid volume / PETG mass at 100 percent",
            f"{volume_cm3:.1f} cm3 / {mass:.0f} g",
            "reported",
            True,
            "printed infill lowers both; the base plate and walls want 3 or more perimeters",
        )
    )

    checks.append(
        Check(
            "slot count",
            f"{len(field.slots())}",
            "reported",
            len(field.slots()) > 0,
        )
    )
    return checks


def report(spec: RiserSpec, checks: list[Check]) -> str:
    lines = [
        (
            f"{spec.id}: {spec.length_mm:.1f} x {spec.depth_mm:.1f} mm, "
            f"deck {spec.low_height_mm:.2f} low to {spec.high_height_mm:.2f} high "
            f"at {spec.slope_deg:.2f} deg"
        ),
        (
            f"  top sheet {spec.top_thickness_mm:.1f} mm, "
            f"base {spec.base_thickness_mm:.1f} mm, "
            f"wall {spec.wall_thickness_mm:.1f} mm"
        ),
        (
            f"  slot field: {len(spec.field.slots())} slots, "
            f"{spec.field.slot_width_mm:.1f} wide / {spec.field.rib_width_mm:.1f} rib / "
            f"{spec.field.slot_length_mm:.1f} long, R{spec.field.end_radius_mm:.1f}"
        ),
        (
            f"  clips: 2 at {spec.clip_spacing_mm:.1f} mm, "
            f"{spec.section.width_along_slot_mm:.1f} wide, section from commons"
        ),
        "",
    ]
    for check in checks:
        mark = "ok  " if check.ok else "FAIL"
        lines.append(f"  [{mark}] {check.name}: {check.value} (want {check.limit})")
        if check.note:
            lines.append(f"         {check.note}")
    failed = [c for c in checks if not c.ok]
    lines.append("")
    lines.append(f"  {len(checks) - len(failed)}/{len(checks)} checks passed")
    return "\n".join(lines)


def export(shape: cq.Workplane, stem: str, formats: str, out: pathlib.Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    wanted = ("step", "stl") if formats == "both" else (formats,)
    for fmt in wanted:
        path = out / f"{stem}.{fmt}"
        cq.exporters.export(shape, str(path))
        print(f"wrote {path}")


# --------------------------------------------------------------------------- #
# command line
# --------------------------------------------------------------------------- #


def _configs() -> dict[str, pathlib.Path]:
    return {path.stem: path for path in sorted(CFG.glob("riser_*.json"))}


def main(argv: list[str] | None = None) -> int:
    configs = _configs()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="riser_two_125b" if "riser_two_125b" in configs else None,
        help="riser config id (the file stem in cfg/)",
    )
    parser.add_argument("--list", action="store_true", help="list the riser configs")
    parser.add_argument(
        "--part",
        choices=("all", "base", "body", "top", "clip"),
        default="all",
        help="which geometry to build (default: all)",
    )
    parser.add_argument("--format", choices=("step", "stl", "both"), default="both")
    parser.add_argument("--out", type=pathlib.Path, default=DWG)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report the derived geometry and checks only",
    )
    args = parser.parse_args(argv)

    if args.list:
        for stem in configs:
            print(stem)
        return 0
    if not args.config:
        parser.error("no riser configs found in cfg/")
    if args.config not in configs:
        parser.error(
            f"unknown config {args.config!r}; choose from {', '.join(configs)}"
        )

    spec = load(configs[args.config])

    if args.part == "base":
        export(build_base(spec), f"{spec.id}_base", args.format, args.out)
        return 0
    if args.part == "body":
        export(build_body(spec), f"{spec.id}_body", args.format, args.out)
        return 0
    if args.part == "top":
        export(build_top(spec), f"{spec.id}_top", args.format, args.out)
        return 0
    if args.part == "clip":
        for index, y in enumerate(spec.clip_centres_y_mm):
            export(
                build_clip(spec, y), f"{spec.id}_clip_{index}", args.format, args.out
            )
        return 0

    part = build(spec)
    checks = validate(spec, part)
    print(report(spec, checks))
    if args.check:
        return 0 if all(c.ok for c in checks) else 1
    export(part, spec.id, args.format, args.out)
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
