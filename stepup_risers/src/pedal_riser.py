"""Reproduce Warwick's QuickMount Pedal Riser from its own sheet, as a solid.

``ref/PedalRiser.pdf`` is the product the printed risers copy: a sloped deck that
carries the board's slot field, so a QuickMount plate drops on, standing on rubber
pads. The sheet is a raster with no text layer, so nothing here is copied from a
text layer; every number is either printed on the sheet and read by eye against
the sheet's own dimensions, or derived from two printed numbers. The review in
``ref/stepup_geometry_review.md`` records which is which.

What the sheet says:

* one 2.0 mm steel sheet, bent four times: a 20.0 front wall, a deck falling toward
  the front, a 41.0 rear wall, and a 22.0 foot turned inboard at each end. The
  sheet's own edge measures 2.04 mm on the raster, and PedalRiser-L's title block
  prints "material: steel, 2,0 mm powdercoated black";
* two slots across the deck, 18.0 wide, 76.0 clear between them and min. 8.0 to
  each side edge - the board's own vocabulary, so the slot is 60.0 long with R4
  ends. They are cut square to the deck's plane, as a punched sheet's would be;
* each end wall is interrupted by a centre gap 33.0 wide whose top stands 35.0
  above the feet, 6.0 below the deck's edge, leaving a leg at each corner;
* four rubber pads, D18 x 5.0, one under each corner leg.

The 121.0 the review took for the envelope is a reference, not the length: it runs
from the front lip station (12.0 from the end face) to the rear wall's inner face,
and 121.0 + 12.0 + 2.0 is how the 135.0 length was derived. PedalRiser-L repeats
the same 121 on a 134.5 deep part.

Datum is the config's: origin at the centre of the 135 x 76 footprint on the
metal's own bottom face, +X across the width, +Y toward the high rear edge, +Z up
parallel to both end walls. The metal occupies z = 0..41, the pads z = -5..0, and
the board plane is therefore z = -5.

    .venv/Scripts/python stepup_risers/src/pedal_riser.py
    .venv/Scripts/python stepup_risers/src/pedal_riser.py --check
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
DEFAULT_CONFIG = PROJECT / "cfg" / "pedal_riser.json"
DWG = PROJECT / "dwg"

LEN_TOL_MM = 0.02

# Slack for booleans and for the inspect-by-section probes. None of these are part
# dimensions: they only have to clear a face and be small enough not to change what
# a cut or a probe selects.
CUT_MARGIN_MM = 1.0
PROBE_MM = 0.5

# Material constants, not part dimensions: the sheet is steel as PedalRiser-L
# prints, and the pads are rubber. Only the mass line uses them.
DENSITY_STEEL_G_CM3 = 7.85
DENSITY_RUBBER_G_CM3 = 1.2


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Spec:
    raw: dict
    id: str
    length_mm: float
    width_mm: float
    height_mm: float
    overall_height_mm: float
    thickness_mm: float
    front_edge_mm: float
    rear_edge_mm: float
    foot_depth_mm: float
    lip_station_mm: float
    reference_span_mm: float
    slot_count: int
    slot_width_mm: float
    slot_length_mm: float
    slot_end_radius_mm: float
    slot_gap_mm: float
    slot_margin_mm: float
    gap_width_mm: float
    gap_top_below_mm: float
    pad_count: int
    pad_diameter_mm: float
    pad_thickness_mm: float
    pad_inset_end_mm: float
    pad_inset_side_mm: float

    @property
    def half_length_mm(self) -> float:
        return self.length_mm / 2.0

    @property
    def half_width_mm(self) -> float:
        return self.width_mm / 2.0

    @property
    def slope_deg(self) -> float:
        """The deck plane's fall, from the two printed heights over the length."""
        return math.degrees(
            math.atan2(self.rear_edge_mm - self.front_edge_mm, self.length_mm)
        )

    @property
    def deck_drop_mm(self) -> float:
        """How far the deck's underside sits below its top face, measured vertically."""
        return self.thickness_mm / math.cos(math.radians(self.slope_deg))

    @property
    def deck_rise_mm(self) -> float:
        return self.rear_edge_mm - self.front_edge_mm

    @property
    def inner_front_mm(self) -> float:
        """Where the deck's underside meets the front wall's inner face."""
        return (
            self.front_edge_mm
            - self.deck_drop_mm
            + self.thickness_mm * math.tan(math.radians(self.slope_deg))
        )

    @property
    def inner_rear_mm(self) -> float:
        return (
            self.rear_edge_mm
            - self.deck_drop_mm
            - self.thickness_mm * math.tan(math.radians(self.slope_deg))
        )

    @property
    def slot_inset_mm(self) -> float:
        """End face to the near edge of a slot, in plan.

        The slot is cut square to the deck, so its plan width is ``width * cos`` and
        the 76.0 the sheet prints is the clear span between the two in plan.
        """
        return self.half_length_mm - self.slot_gap_mm / 2.0 - self.slot_plan_width_mm

    @property
    def slot_plan_width_mm(self) -> float:
        return self.slot_width_mm * math.cos(math.radians(self.slope_deg))

    @property
    def slot_centre_y_mm(self) -> float:
        """Plan centre of a slot, placed so the printed 76.0 clear gap closes."""
        return self.slot_gap_mm / 2.0 + self.slot_plan_width_mm / 2.0

    @property
    def leg_width_mm(self) -> float:
        return (self.width_mm - self.gap_width_mm) / 2.0

    @property
    def pad_centre_x_mm(self) -> float:
        return self.half_width_mm - self.pad_inset_side_mm

    @property
    def pad_centre_y_mm(self) -> float:
        return self.half_length_mm - self.pad_inset_end_mm

    def deck_top_z(self, y_mm: float) -> float:
        """Height of the deck's top face above the feet's underside at +y."""
        return self.front_edge_mm + (y_mm + self.half_length_mm) * math.tan(
            math.radians(self.slope_deg)
        )

    @property
    def pad_volume_mm3(self) -> float:
        return (
            self.pad_count
            * math.pi
            * (self.pad_diameter_mm / 2.0) ** 2
            * (self.pad_thickness_mm)
        )


def _require(node: dict, key: str, where: str) -> float:
    if key not in node or node[key] is None:
        raise ValueError(f"{where}: {key} is unset; a null blocks generation")
    return float(node[key])


def load(path: pathlib.Path = DEFAULT_CONFIG) -> Spec:
    if not path.exists():
        raise FileNotFoundError(f"config is missing: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    name = path.name

    envelope = raw["envelope"]
    section = raw["section"]
    slots = raw["deck_slots"]
    legs = raw["legs"]
    pads = raw["pads"]

    spec = Spec(
        raw=raw,
        id=str(raw["id"]),
        length_mm=_require(envelope, "length_mm", name),
        width_mm=_require(envelope, "width_mm", name),
        height_mm=_require(envelope, "height_mm", name),
        overall_height_mm=_require(envelope, "overall_height_mm", name),
        thickness_mm=_require(envelope, "sheet_thickness_mm", name),
        front_edge_mm=_require(section, "front_edge_height_mm", name),
        rear_edge_mm=_require(section, "rear_edge_height_mm", name),
        foot_depth_mm=_require(section, "foot_depth_mm", name),
        lip_station_mm=_require(section, "front_lip_station_mm", name),
        reference_span_mm=_require(section, "reference_span_mm", name),
        slot_count=int(_require(slots, "count", name)),
        slot_width_mm=_require(slots, "width_mm", name),
        slot_length_mm=_require(slots, "length_mm", name),
        slot_end_radius_mm=_require(slots, "end_radius_mm", name),
        slot_gap_mm=_require(slots, "clear_gap_mm", name),
        slot_margin_mm=_require(slots, "edge_margin_mm", name),
        gap_width_mm=_require(legs, "gap_width_mm", name),
        gap_top_below_mm=_require(legs, "gap_top_below_edge_mm", name),
        pad_count=int(_require(pads, "count", name)),
        pad_diameter_mm=_require(pads, "diameter_mm", name),
        pad_thickness_mm=_require(pads, "thickness_mm", name),
        pad_inset_end_mm=_require(pads, "inset_from_end_mm", name),
        pad_inset_side_mm=_require(pads, "inset_from_side_mm", name),
    )

    # The derived values the drawing's callouts have to close against. A config
    # that no longer closes is a config that needs re-reading, not clipping.
    if spec.slot_count != 2:
        raise ValueError(
            f"{name}: this sheet carries two deck slots, not {spec.slot_count}"
        )
    if not math.isclose(
        spec.slot_margin_mm,
        (spec.width_mm - spec.slot_length_mm) / 2.0,
        abs_tol=LEN_TOL_MM,
    ):
        raise ValueError(
            f"{name}: slot length {spec.slot_length_mm} and edge margin "
            f"{spec.slot_margin_mm} do not close on the {spec.width_mm} width"
        )
    if not math.isclose(
        spec.reference_span_mm,
        spec.length_mm - spec.lip_station_mm - spec.thickness_mm,
        abs_tol=LEN_TOL_MM,
    ):
        raise ValueError(
            f"{name}: the printed {spec.reference_span_mm} reference, the "
            f"{spec.lip_station_mm} lip station and the {spec.thickness_mm} sheet "
            f"do not chain to the {spec.length_mm} length"
        )
    if not math.isclose(
        spec.pad_thickness_mm,
        spec.overall_height_mm - spec.height_mm,
        abs_tol=LEN_TOL_MM,
    ):
        raise ValueError(
            f"{name}: {spec.overall_height_mm} over the pads less {spec.height_mm} "
            f"of metal is not the {spec.pad_thickness_mm} pad"
        )
    if not (
        spec.pad_inset_end_mm - spec.pad_diameter_mm / 2.0 >= -LEN_TOL_MM
        and spec.pad_inset_end_mm + spec.pad_diameter_mm / 2.0
        <= spec.foot_depth_mm + LEN_TOL_MM
    ):
        raise ValueError(
            f"{name}: a D{spec.pad_diameter_mm} pad set {spec.pad_inset_end_mm} from "
            f"the end does not fit inside the {spec.foot_depth_mm} foot"
        )
    if not (
        spec.pad_centre_x_mm - spec.pad_diameter_mm / 2.0
        >= spec.gap_width_mm / 2.0 - LEN_TOL_MM
        and spec.pad_centre_x_mm + spec.pad_diameter_mm / 2.0
        <= spec.half_width_mm + LEN_TOL_MM
    ):
        raise ValueError(
            f"{name}: a D{spec.pad_diameter_mm} pad at x {spec.pad_centre_x_mm} does "
            f"not sit between the {spec.gap_width_mm} wall gap and the {spec.width_mm} edge"
        )
    return spec


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #


def section_points(spec: Spec) -> list[tuple[float, float]]:
    """The bent strip seen end-on, as a closed (y, z) loop.

    Outer surface first - front wall, deck top, rear wall - then back along the
    underside through both feet, so the loop is the sheet's own cross-section and
    nothing in it is restated: the deck's underside falls out of the thickness and
    the slope.
    """
    length = spec.length_mm
    sheet = spec.thickness_mm
    foot = spec.foot_depth_mm
    return [
        (0.0, 0.0),
        (0.0, spec.front_edge_mm),
        (length, spec.rear_edge_mm),
        (length, 0.0),
        (length - foot, 0.0),
        (length - foot, sheet),
        (length - sheet, sheet),
        (length - sheet, spec.inner_rear_mm),
        (sheet, spec.inner_front_mm),
        (sheet, sheet),
        (foot, sheet),
        (foot, 0.0),
    ]


def metal(spec: Spec) -> cq.Workplane:
    """The sheet: one closed section, swept across the width."""
    points = section_points(spec)
    # "YZ" puts local x on +Y and local y on +Z, and extrudes along +X.
    wp = cq.Workplane("YZ").moveTo(*points[0])
    for point in points[1:]:
        wp = wp.lineTo(*point)
    body = wp.close().extrude(spec.width_mm)
    return body.translate((-spec.half_width_mm, -spec.half_length_mm, 0.0))


def slot_tools(spec: Spec) -> list[cq.Solid]:
    """Two 18.0 x 60.0 slots with R4 ends, cut square to the deck's own plane."""
    tools: list[cq.Solid] = []
    reach = spec.thickness_mm + CUT_MARGIN_MM
    for sign in (-1.0, 1.0):
        y_mm = sign * spec.slot_centre_y_mm
        cutter = (
            cq.Workplane("XY")
            .rect(spec.slot_length_mm, spec.slot_width_mm)
            .extrude(2.0 * reach)
            .translate((0.0, 0.0, -reach))
        )
        cutter = cutter.edges("|Z").fillet(spec.slot_end_radius_mm)
        # The slot walls follow the deck's normal, so the saw is tipped with it.
        cutter = cutter.rotate((0, 0, 0), (1, 0, 0), spec.slope_deg)
        z_mm = spec.deck_top_z(y_mm) - spec.deck_drop_mm / 2.0
        tools.append(cutter.val().translate(cq.Vector(0.0, y_mm, z_mm)))
    return tools


def leg_tool(spec: Spec, front: bool) -> cq.Solid:
    """The centre gap in one end wall, open to the foot and stopping 6.0 short."""
    reach = spec.thickness_mm + CUT_MARGIN_MM
    face = -spec.half_length_mm if front else spec.half_length_mm
    sign = 1.0 if front else -1.0
    y0, y1 = sorted((face, face + sign * reach))
    top = (spec.front_edge_mm if front else spec.rear_edge_mm) - spec.gap_top_below_mm
    return _box(
        -spec.gap_width_mm / 2.0,
        spec.gap_width_mm / 2.0,
        y0,
        y1,
        spec.thickness_mm,
        top,
    )


def pads(spec: Spec) -> list[cq.Solid]:
    """Four D18 rubber pads, one under each corner leg."""
    return [
        _cylinder(
            spec.pad_diameter_mm,
            -spec.pad_thickness_mm,
            0.0,
            sign_x * spec.pad_centre_x_mm,
            sign_y * spec.pad_centre_y_mm,
        )
        for sign_x in (-1.0, 1.0)
        for sign_y in (-1.0, 1.0)
    ]


def build(spec: Spec) -> cq.Workplane:
    """The finished part: the sheet, its slots and wall gaps, and the four pads."""
    part = metal(spec)
    part = _cut(part, slot_tools(spec) + [leg_tool(spec, True), leg_tool(spec, False)])
    for pad in pads(spec):
        part = part.union(cq.Workplane("XY").add(pad))
    return part.clean()


def _box(x0, x1, y0, y1, z0, z1) -> cq.Solid:
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def _cylinder(dia: float, z0: float, z1: float, x: float, y: float) -> cq.Solid:
    return cq.Solid.makeCylinder(
        dia / 2.0, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1)
    )


def _cut(wp: cq.Workplane, tools: list[cq.Solid]) -> cq.Workplane:
    stack = cq.Workplane("XY")
    for tool in tools:
        stack = stack.add(tool)
    return wp.cut(stack)


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


def _band(solid: cq.Solid, x0, x1, y0, y1, z0, z1) -> list:
    cut = solid.intersect(_box(x0, x1, y0, y1, z0, z1))
    return sorted(
        cut.Solids(), key=lambda s: (s.BoundingBox().ymin, s.BoundingBox().xmin)
    )


def _wall_edge(solid: cq.Solid, y_face: float, tol: float = 0.01) -> float:
    """Top of the wall whose outer face lies on +-y_face, as the sheet prints it.

    The corner has to be read off the face itself: a probe band just inside the
    end carries the deck's fall, so it would report the slope rather than the
    height the drawing dimensions.
    """
    tops = [
        face.BoundingBox().zmax
        for face in solid.Faces()
        if abs(face.BoundingBox().ymin - y_face) < tol
        and abs(face.BoundingBox().ymax - y_face) < tol
    ]
    return max(tops) if tops else float("nan")


def _level(solid: cq.Solid, spec: Spec) -> tuple[cq.Solid, float]:
    """The part turned until the deck is horizontal, and the deck's top plane.

    Every deck probe goes through here: with the deck flat, a slot's own width and
    length read directly, instead of a projection of them.
    """
    level = solid.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -spec.slope_deg)
    slope = math.radians(spec.slope_deg)
    top = spec.half_length_mm * math.sin(slope) + spec.front_edge_mm * math.cos(slope)
    return level, top


def validate(spec: Spec, part: cq.Workplane) -> list[Check]:
    solid = part.val()
    box = solid.BoundingBox()
    checks: list[Check] = []

    def exact(name, value, wanted, note=""):
        checks.append(
            Check(
                name,
                f"{value:.2f} mm",
                f"{wanted:.2f} mm",
                abs(value - wanted) <= LEN_TOL_MM,
                note,
            )
        )

    def flag(name, value, limit, ok, note=""):
        checks.append(Check(name, value, limit, bool(ok), note))

    half_w, half_l = spec.half_width_mm, spec.half_length_mm
    sheet = spec.thickness_mm
    reach = 10.0
    edge = half_w - 2.0

    exact("overall length", box.ylen, spec.length_mm, "135.0, the 121 + 12 + 2 chain")
    exact("overall width", box.xlen, spec.width_mm, "76.0, both sheets")
    exact("metal height", box.zmax, spec.height_mm, "41.0 to the rear top corner")
    exact(
        "overall height over the pads",
        box.zmax - box.zmin,
        spec.overall_height_mm,
        "41.0 of metal plus the 5.0 pads",
    )
    exact("pads below the metal", box.zmin, -spec.pad_thickness_mm, "the board plane")

    # One corner leg, clear of both centre gaps: the sheet's own thickness, then the
    # rear wall's inner face that the 121.0 reference is measured from.
    wall = _band(
        solid,
        edge - 5.0,
        edge - 1.0,
        -half_l - reach,
        half_l + reach,
        sheet + 2.0,
        sheet + 6.0,
    )
    exact(
        "sheet thickness",
        wall[0].BoundingBox().ylen if wall else float("nan"),
        sheet,
        "2.04 read off the raster, steel 2.0 on PedalRiser-L",
    )
    rear_wall = max((s.BoundingBox() for s in wall), key=lambda b: b.ymin, default=None)
    exact(
        "rear wall inner face",
        (rear_wall.ymin + half_l) if rear_wall else float("nan"),
        spec.length_mm - sheet,
        "the 121.0 reference runs from here",
    )
    exact(
        f"{spec.reference_span_mm:g} reference",
        ((rear_wall.ymin + half_l) if rear_wall else float("nan"))
        - spec.lip_station_mm,
        spec.reference_span_mm,
        f"inner face less the {spec.lip_station_mm:g} front lip station",
    )

    exact(
        "front edge height",
        _wall_edge(solid, -half_l),
        spec.front_edge_mm,
        "20.0 printed, the corner at the front face",
    )
    exact(
        "rear edge height",
        _wall_edge(solid, half_l),
        spec.rear_edge_mm,
        "41.0 printed, the corner at the rear face",
    )

    # The deck's plane, sampled well clear of the slots: the two printed heights and
    # the length have to put it where the section says.
    for y_mm in (-30.0, 30.0):
        deck = _band(
            solid,
            8.0,
            16.0,
            y_mm - PROBE_MM,
            y_mm + PROBE_MM,
            -reach,
            spec.rear_edge_mm + reach,
        )
        exact(
            f"deck height at y {y_mm:+.0f}",
            max((s.BoundingBox().zmax for s in deck), default=float("nan")),
            spec.deck_top_z(y_mm + PROBE_MM),
            f"the plane falls {spec.slope_deg:.2f} deg",
        )

    # The feet: a horizontal slice through the sheet's own thickness at each end.
    feet = _band(
        solid,
        -edge,
        edge,
        -half_l - reach,
        half_l + reach,
        sheet / 2.0 - 0.25,
        sheet / 2.0 + 0.25,
    )
    front_foot = min((s.BoundingBox().ymax for s in feet), default=float("nan"))
    rear_foot = max((s.BoundingBox().ymin for s in feet), default=float("nan"))
    exact(
        "foot depth, front",
        front_foot + half_l,
        spec.foot_depth_mm,
        "22.0 printed on the bottom view",
    )
    exact(
        "foot depth, rear",
        half_l - rear_foot,
        spec.foot_depth_mm,
        "22.0 printed on the bottom view",
    )
    exact(
        "foot inboard of the wall",
        spec.foot_depth_mm - sheet,
        20.0,
        "22.0 less the sheet",
    )

    # Centre gaps: open in the middle, a leg at each corner, and a top at 35.0.
    for name, face in (("front", -half_l), ("rear", half_l)):
        gap_top = (spec.front_edge_mm if name == "front" else spec.rear_edge_mm) - (
            spec.gap_top_below_mm
        )
        # Keep every probe below the deck that closes over the gap.
        open_middle = _band(
            solid, -4.0, 4.0, face - reach, face + reach, sheet + 1.0, gap_top - 2.0
        )
        flag(
            f"{name} gap open",
            f"{len(open_middle)} solid(s)",
            "0",
            not open_middle,
            f"{spec.gap_width_mm:.1f} wide, open to the foot",
        )
        strip = _band(
            solid,
            -4.0,
            4.0,
            face - reach,
            face + reach,
            sheet + 1.0,
            spec.rear_edge_mm + reach,
        )
        exact(
            f"{name} gap top",
            min((s.BoundingBox().zmin for s in strip), default=float("nan")),
            gap_top,
            f"{spec.gap_top_below_mm:g} below the deck's edge",
        )
        legs = _band(
            solid,
            -half_w - 1.0,
            half_w + 1.0,
            face - reach,
            face + reach,
            sheet + 2.0,
            gap_top - 2.0,
        )
        span = (
            min(s.BoundingBox().xmin for s in legs if s.BoundingBox().xmin > 0)
            - max(s.BoundingBox().xmax for s in legs if s.BoundingBox().xmax < 0)
            if len(legs) == 2
            else float("nan")
        )
        exact(
            f"{name} gap width", span, spec.gap_width_mm, "33.0 printed on the end view"
        )
        if len(legs) == 2:
            exact(
                f"{name} leg width",
                max(s.BoundingBox().xlen for s in legs),
                spec.leg_width_mm,
                f"({spec.width_mm:g} - {spec.gap_width_mm:g}) / 2",
            )

    # The deck, probed with the deck flat so that a slot reads at its own size
    # rather than at its projection. A lane inside the slots' 60 mm splits the deck
    # into three: the tail before the front slot, the 76.0 between them, and the
    # tail behind the rear slot.
    level, deck_top = _level(solid, spec)
    z0 = deck_top - spec.deck_drop_mm * 0.7
    z1 = deck_top - spec.deck_drop_mm * 0.3
    plan = math.cos(math.radians(spec.slope_deg))

    tails = _band(level, -8.0, 8.0, -half_l - 2.0, half_l + 2.0, z0, z1)
    flag(
        "deck split by its slots",
        f"{len(tails)} solid(s)",
        "3",
        len(tails) == 3,
        "a lane down the middle of the deck passes both slots",
    )
    if len(tails) == 3:
        cuts = [
            tails[1].BoundingBox().ymin - tails[0].BoundingBox().ymax,
            tails[2].BoundingBox().ymin - tails[1].BoundingBox().ymax,
        ]
        exact(
            "slot width",
            sum(cuts) / 2.0,
            spec.slot_width_mm,
            "18.0 printed, normal to the deck",
        )
        exact(
            "clear gap between the slots",
            tails[1].BoundingBox().ylen * plan,
            spec.slot_gap_mm,
            "76.0 printed, in plan across the deck's fall",
        )
        # Inside the front slot, clear of its R4 corners: only the flanks outside
        # its 60 mm survive.
        corner = spec.slot_end_radius_mm + 1.0
        slot_lo = tails[0].BoundingBox().ymax + corner
        slot_hi = tails[1].BoundingBox().ymin - corner
        flanks = _band(level, -half_w - 2.0, half_w + 2.0, slot_lo, slot_hi, z0, z1)
        left = [s.BoundingBox() for s in flanks if s.BoundingBox().xmax < 0.0]
        right = [s.BoundingBox() for s in flanks if s.BoundingBox().xmin > 0.0]
        exact(
            "slot length",
            (-left[0].xmax + right[0].xmin) if left and right else float("nan"),
            spec.slot_length_mm,
            f"{spec.width_mm:g} less 2 x {spec.slot_margin_mm:g} of edge",
        )
        exact(
            "slot edge margin",
            left[0].xlen if left else float("nan"),
            spec.slot_margin_mm,
            "min. 8.0 printed",
        )

    # Pads.
    pad_band = _band(
        solid,
        -half_w - reach,
        half_w + reach,
        -half_l - reach,
        half_l + reach,
        -spec.pad_thickness_mm + 0.5,
        -spec.pad_thickness_mm + 1.5,
    )
    flag(
        "pads",
        f"{len(pad_band)} solid(s)",
        str(spec.pad_count),
        len(pad_band) == spec.pad_count,
        f"D{spec.pad_diameter_mm:g} x {spec.pad_thickness_mm:g}, one per corner leg",
    )
    if pad_band:
        exact(
            "pad diameter",
            max(s.BoundingBox().xlen for s in pad_band),
            spec.pad_diameter_mm,
            "18 across, read off the bottom view",
        )
        exact(
            "pad pitch across",
            max(s.BoundingBox().xmax for s in pad_band)
            - min(s.BoundingBox().xmin for s in pad_band),
            2.0 * spec.pad_centre_x_mm + spec.pad_diameter_mm,
            "the two pads of one foot",
        )

    flag(
        "solid count",
        str(len(solid.Solids())),
        "1",
        len(solid.Solids()) == 1,
        "the sheet and its four pads are one body",
    )
    metal_volume = solid.Volume() - spec.pad_volume_mm3
    mass = (
        metal_volume / 1000.0 * DENSITY_STEEL_G_CM3
        + spec.pad_volume_mm3 / 1000.0 * DENSITY_RUBBER_G_CM3
    )
    flag(
        "volume",
        f"{metal_volume:.0f} mm3",
        "> 0",
        metal_volume > 0.0,
        f"{mass:.0f} g: {metal_volume / 1000.0 * DENSITY_STEEL_G_CM3:.0f} g of steel, "
        f"{spec.pad_volume_mm3 / 1000.0 * DENSITY_RUBBER_G_CM3:.0f} g of rubber",
    )
    return checks


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #


def report(spec: Spec, checks: list[Check], out: pathlib.Path | None) -> str:
    lines = [
        f"{spec.id}{'  (' + pathlib.Path(out).name + ')' if out else ''}",
        "",
        "sheet, read from ref/PedalRiser.pdf",
        f"  length                {spec.length_mm:7.2f} mm   121.0 + 12.0 + 2.0, not printed",
        f"  width                 {spec.width_mm:7.2f} mm   76.0 printed",
        f"  thickness             {spec.thickness_mm:7.2f} mm   2.04 on the raster, steel on PedalRiser-L",
        f"  front edge            {spec.front_edge_mm:7.2f} mm   20.0 printed",
        f"  rear edge             {spec.rear_edge_mm:7.2f} mm   41.0 printed",
        f"  deck fall             {spec.slope_deg:7.2f} deg  atan({spec.deck_rise_mm:g} / {spec.length_mm:g})",
        f"  feet                  {spec.foot_depth_mm:7.2f} mm   22.0 printed, {spec.foot_depth_mm - spec.thickness_mm:.1f} inboard of the wall",
        f"  overall height        {spec.overall_height_mm:7.2f} mm   over the pads",
        "",
        "deck",
        (
            f"  slots                 {spec.slot_count} x {spec.slot_width_mm:g} x "
            f"{spec.slot_length_mm:g}, R{spec.slot_end_radius_mm:g} ends, "
            "square to the deck"
        ),
        f"  clear between         {spec.slot_gap_mm:7.2f} mm   76.0 printed",
        f"  edge margin           {spec.slot_margin_mm:7.2f} mm   min. 8.0 printed",
        f"  inset from each end   {spec.slot_inset_mm:7.2f} mm   derived from the 76.0 gap",
        "",
        "legs",
        f"  centre gap            {spec.gap_width_mm:7.2f} mm   33.0 printed",
        f"  gap top, rear         {spec.rear_edge_mm - spec.gap_top_below_mm:7.2f} mm   35.0 printed above the feet",
        f"  gap top, front        {spec.front_edge_mm - spec.gap_top_below_mm:7.2f} mm   same 6.0 rule, not printed",
        f"  corner legs           {spec.leg_width_mm:7.2f} mm   each side of the gap",
        "",
        "pads",
        (
            f"  {spec.pad_count} x D{spec.pad_diameter_mm:g} x "
            f"{spec.pad_thickness_mm:g}   at (+/-{spec.pad_centre_x_mm:.2f}, "
            f"+/-{spec.pad_centre_y_mm:.2f})"
        ),
        (
            f"  front lip station     {spec.lip_station_mm:7.2f} mm   12.0 printed; "
            "the lip itself is not modelled"
        ),
        (
            f"  {spec.reference_span_mm:g} reference        "
            f"{spec.length_mm - spec.lip_station_mm - spec.thickness_mm:7.2f} mm   "
            "lip station to the rear wall's inner face"
        ),
        "",
        "checks",
    ]

    width = max(len(c.name) for c in checks)
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        lines.append(
            f"  {mark} {c.name:<{width}}  {c.value:>14}  {c.limit:>14}  {c.note}"
        )
    failed = [c for c in checks if not c.ok]
    lines.append("")
    lines.append(
        f"{len(checks) - len(failed)}/{len(checks)} checks pass"
        if not failed
        else f"{len(failed)} CHECK(S) FAILED"
    )
    return "\n".join(lines)


def summary(spec: Spec, checks: list[Check], out: pathlib.Path) -> dict:
    return {
        "id": spec.id,
        "stl": str(out),
        "envelope_mm": {
            "length": spec.length_mm,
            "width": spec.width_mm,
            "height": spec.height_mm,
            "overall_height": spec.overall_height_mm,
            "sheet_thickness": spec.thickness_mm,
        },
        "section_mm": {
            "front_edge": spec.front_edge_mm,
            "rear_edge": spec.rear_edge_mm,
            "deck_slope_deg": round(spec.slope_deg, 3),
            "foot_depth": spec.foot_depth_mm,
            "front_lip_station": spec.lip_station_mm,
            "reference_span": spec.reference_span_mm,
        },
        "deck_slots": {
            "count": spec.slot_count,
            "width": spec.slot_width_mm,
            "length": spec.slot_length_mm,
            "end_radius": spec.slot_end_radius_mm,
            "clear_gap": spec.slot_gap_mm,
            "edge_margin": spec.slot_margin_mm,
            "inset_from_end": round(spec.slot_inset_mm, 3),
        },
        "legs": {
            "gap_width": spec.gap_width_mm,
            "gap_top_below_edge": spec.gap_top_below_mm,
            "leg_width": spec.leg_width_mm,
        },
        "pads": {
            "count": spec.pad_count,
            "diameter": spec.pad_diameter_mm,
            "thickness": spec.pad_thickness_mm,
            "x": spec.pad_centre_x_mm,
            "y": spec.pad_centre_y_mm,
        },
        "open_questions": [q for q in spec.raw.get("open_questions", [])],
        "checks": [
            {"name": c.name, "value": c.value, "limit": c.limit, "ok": c.ok}
            for c in checks
        ],
        "ok": all(c.ok for c in checks),
    }


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def export(shape: cq.Workplane, out: pathlib.Path, tolerance: float) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(shape, str(out), tolerance=tolerance, angularTolerance=0.1)
    cq.exporters.export(shape, str(out.with_suffix(".step")))
    print(f"wrote {out}")
    print(f"wrote {out.with_suffix('.step')}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    ap.add_argument(
        "--out",
        type=pathlib.Path,
        default=DWG / "pedal_riser.stl",
        help="STL to write, with the STEP beside it",
    )
    ap.add_argument("--check", action="store_true", help="report the checks only")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    ap.add_argument(
        "--tolerance", type=float, default=0.01, help="STL linear tolerance"
    )
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    spec = load(args.config)
    part = build(spec)
    checks = validate(spec, part)
    ok = all(c.ok for c in checks)

    if args.json:
        print(json.dumps(summary(spec, checks, args.out), indent=2))
    else:
        print(report(spec, checks, None if args.check else args.out))
    if not args.check:
        export(part, args.out, args.tolerance)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
