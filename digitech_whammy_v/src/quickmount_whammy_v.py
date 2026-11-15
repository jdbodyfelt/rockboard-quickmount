"""Generate the QuickMount parts for the DigiTech Whammy V.

The pedal gives this mount one hard constraint and one surprise. The hard constraint is
that its underside is a plain pressed pan with four glued rubber pads and no fastener of
any kind, so nothing can clamp it from below. The surprise is that its top plate is held
by five black hex-socket screws, and a screw head is a surface a bracket *can* bear on.

A top-plate screw cannot pull the pedal down - tightening one clamps the bracket to the
pedal and the force circulates inside the pedal's own boss. What a head's flat top does
give is a bearing face, and that is enough: the pedal's lift is carried through the head,
into a collar's roof, down the holder's wall, into the plate, into the clips and so into
the board's ribs. The one consequence is that a collar has to come *down* over its head,
which nothing moulded into the plate can do once the pedal is standing on that plate.

So the set is four parts:

* the **baseplate**, with four QuickMount clips and a 6 mm side ledge along each long
  edge - the ledge is what the holders bolt to, and it doubles as edge stiffening;
* two **twofer rails**, one per long side, each carrying a collar over both of its heads;
* the **toe arm**, a separate part for screw D, which is 60 mm inboard of anything a rail
  can reach and hangs off a bar along the pedal's toe end instead.

The clip section is not restated here and is not imported from ``commons/src`` either:
it is read in from ``commons/cfg/retainer.json`` at load time, so this plate stays a
self-contained module while a corrected wall or ledge still moves every plate at once.
The plate's 3 mm thickness is part of that contract - the retainer's blade finishes
flush with the plate's top face - so the loader refuses any other thickness.

Datum is the config's: plate board-facing face centre, +X across the pedal's width
toward the button panel, +Y toward the INPUT/MIDI end, +Z from the board-facing face
toward the pedal. The plate occupies z = 0..3, the side ledges 0..9, the clips hang at
z < 0, the pedal's pan sits at z = 3.2, its top face at 47.9 and the collar tops at 51.6.

    .venv/Scripts/python digitech_whammy_v/src/quickmount_whammy_v.py
    .venv/Scripts/python digitech_whammy_v/src/quickmount_whammy_v.py --part base
    .venv/Scripts/python digitech_whammy_v/src/quickmount_whammy_v.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT / "cfg" / "digitech_whammy_v.json"
OUT = PROJECT / "dwg"
STEM = "QuickMount-Whammy-V"

CUT_MARGIN_MM = 1.0
TOL_MM = 0.02

# The retainer section is a fixed moulding measured off an OEM Type E, and its blade
# finishes flush with the plate's top face. 18.89 is the drop from that face, so a
# thicker plate lengthens the blade and detunes the retention it was measured for.
SECTION_DROP_MM = 18.89
SECTION_PLATE_MM = 3.0


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Section:
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
        """The blade's tip finishes flush with the plate's top face, in the window."""
        return self.plate_thickness_mm


@dataclass
class Spec:
    raw: dict
    sites: dict[str, tuple[float, float]]
    head_dia_mm: float
    head_height_mm: float
    pedal_x_mm: float
    pedal_y_mm: float
    rim_mm: float
    treadle_edge_x_mm: float
    plate_x_mm: float
    plate_y_mm: float
    plate_thickness_mm: float
    corner_radius_mm: float
    basket: dict
    ring: dict
    clip_columns_mm: tuple[float, ...]
    clip_rows_mm: tuple[float, ...]
    clip_width_mm: float
    tool_gap_mm: float
    pad_x_mm: float
    pad_y_mm: float
    pad_dia_mm: float
    pad_depth_mm: float
    collar_dia_mm: float
    pocket_dia_mm: float
    pocket_depth_mm: float
    collar_underside_z_mm: float
    treadle_cut_x_mm: float
    zones: list[dict]
    section: Section = field(repr=False)

    @property
    def half_x_mm(self) -> float:
        return self.plate_x_mm / 2.0

    @property
    def half_y_mm(self) -> float:
        return self.plate_y_mm / 2.0

    @property
    def pedal_half_x_mm(self) -> float:
        return self.pedal_x_mm / 2.0

    @property
    def pedal_half_y_mm(self) -> float:
        return self.pedal_y_mm / 2.0

    @property
    def pan_z_mm(self) -> float:
        """The pedal's bottom face, 0.2 above the plate so its own feet set the height."""
        return self.plate_thickness_mm + 0.2

    @property
    def pedal_top_z_mm(self) -> float:
        return self.pan_z_mm + self.rim_mm

    @property
    def collar_top_z_mm(self) -> float:
        return self.ring["top_z_mm"]

    @property
    def wall_top_z_mm(self) -> float:
        return self.basket["top_z_mm"]

    @property
    def wall_thickness_mm(self) -> float:
        return self.basket["wall_thickness_mm"]

    @property
    def wall_inner_x_mm(self) -> float:
        return self.basket["inner_x_mm"]

    @property
    def ring_thickness_mm(self) -> float:
        return self.ring["thickness_mm"]

    def mouth_y_mm(self, row: float) -> float:
        """Where a window stops: the clip's mouth wall, 6.5 inboard of its centre."""
        sign = 1.0 if row > 0 else -1.0
        return row - sign * self.section.half_mouth_mm


def _read(path: Path, what: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{what} is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load(path: Path = DEFAULT_CONFIG) -> Spec:
    raw = _read(path, "config")
    holders = raw["holders"]
    collar = holders["collar"]

    ref = raw["quickmount"]["clips"]["section"]
    section_cfg = _read((path.parents[1] / ref).resolve(), "retainer section")
    envelope, sec = section_cfg["envelope"], section_cfg["section"]
    section = Section(
        width_along_slot_mm=envelope["width_mm"],
        outer_width_mm=envelope["outer_width_mm"],
        mouth_width_mm=sec["mouth_width_mm"],
        post_wall_mm=sec["post_wall_mm"],
        blade_wall_mm=sec["blade_wall_mm"],
        blade_tip_chamfer_mm=sec["blade_tip_chamfer_mm"],
        ledge_drop_mm=sec["ledge"]["drop_below_plate_mm"],
        ledge_protrusion_mm=sec["ledge"]["protrusion_mm"],
        drop_below_plate_top_mm=envelope["drop_below_plate_top_mm"],
        plate_thickness_mm=envelope["plate_thickness_mm"],
    )
    if abs(section.plate_thickness_mm - SECTION_PLATE_MM) > TOL_MM:
        raise ValueError(
            f"retainer section is drawn for a {section.plate_thickness_mm} plate, not "
            f"{SECTION_PLATE_MM}: the blade tip must finish flush with the plate top"
        )
    if abs(section.drop_below_plate_top_mm - SECTION_DROP_MM) > 0.05:
        raise ValueError("retainer drop no longer matches the measured 18.89")

    plate = raw["quickmount"]["plate"]
    dimples = raw["quickmount"]["pad_dimples"]
    return Spec(
        raw=raw,
        sites={
            k: (v["x_mm"], v["y_mm"])
            for k, v in raw["fasteners"]["oem_top_plate"]["sites"].items()
        },
        head_dia_mm=raw["fasteners"]["oem_top_plate"]["head_dia_mm"],
        head_height_mm=raw["fasteners"]["oem_top_plate"]["head_height_mm"],
        pedal_x_mm=raw["physical"]["width_mm"],
        pedal_y_mm=raw["physical"]["depth_mm"],
        rim_mm=raw["physical"]["rim_height_above_pan_mm"],
        treadle_edge_x_mm=raw["physical"]["treadle_plate_edge_x_mm"],
        plate_x_mm=plate["x_mm"],
        plate_y_mm=plate["y_mm"],
        plate_thickness_mm=plate["thickness_mm"],
        corner_radius_mm=plate["corner_radius_mm"],
        basket=raw["basket"],
        ring=raw["ring"],
        clip_columns_mm=tuple(raw["quickmount"]["clips"]["columns_x_mm"]),
        clip_rows_mm=tuple(raw["quickmount"]["clips"]["rows_y_mm"]),
        clip_width_mm=raw["quickmount"]["clips"]["width_mm"],
        tool_gap_mm=raw["quickmount"]["clips"]["tool_gap_mm"],
        pad_x_mm=dimples["x_mm"],
        pad_y_mm=dimples["y_mm"],
        pad_dia_mm=dimples["dia_mm"],
        pad_depth_mm=dimples["depth_mm"],
        collar_dia_mm=collar["outer_dia_mm"],
        pocket_dia_mm=collar["pocket_dia_mm"],
        pocket_depth_mm=collar["pocket_depth_mm"],
        collar_underside_z_mm=collar["underside_z_mm"],
        treadle_cut_x_mm=raw["ring"]["inner_x_treadle_mm"],
        zones=raw["panel_zones"]["zones"],
        section=section,
    )


# --------------------------------------------------------------------------- #
# primitives
# --------------------------------------------------------------------------- #


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> cq.Solid:
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def _cylinder(dia: float, z0: float, z1: float, x: float, y: float) -> cq.Solid:
    return cq.Solid.makeCylinder(dia / 2.0, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))


def _cut(wp: cq.Workplane, tools: list[cq.Solid]) -> cq.Workplane:
    if not tools:
        return wp
    stack = cq.Workplane("XY")
    for tool in tools:
        stack = stack.add(tool)
    return wp.cut(stack)


def _union(wp: cq.Workplane, tools: list[cq.Solid]) -> cq.Workplane:
    for tool in tools:
        wp = wp.union(cq.Workplane("XY").add(tool))
    return wp


# --------------------------------------------------------------------------- #
# plate
# --------------------------------------------------------------------------- #


def pilot_positions(spec: Spec) -> list[tuple[float, float]]:
    """The six M3 stations, on the basket's wall tops."""
    return [(float(x), float(y)) for x, y in spec.ring["screws"]["stations"]]


def _window_tool(spec: Spec, centre_x_mm: float, row: float) -> cq.Solid:
    """One window: a closed slot, not a notch out through the plate's edge.

    The slot runs from the clip's mouth wall out to an end that stops
    ``clips.tool_gap_mm`` clear of the clip's own silhouette, so the plate keeps a
    continuous rim all the way round. 22 x 21 is too square for a true stadium - the clip's
    arch is 19 deep and the gap takes the rest - so the corners are R4, which keeps a
    14 mm flat on the mouth wall for the clip to spring from.
    """
    sign = 1.0 if row > 0 else -1.0
    floor = abs(spec.mouth_y_mm(row))
    end = abs(row) + spec.section.half_outer_mm + spec.tool_gap_mm
    length = end - floor
    if length <= spec.clip_width_mm * 0.5:
        raise ValueError("window is too short for the clip; widen clips.tool_gap_mm")
    radius = min(4.0, length / 2.0 - 0.1, spec.clip_width_mm / 2.0 - 0.1)
    solid = (
        cq.Workplane("XY")
        .rect(spec.clip_width_mm, length)
        .extrude(spec.plate_thickness_mm + CUT_MARGIN_MM)
        .edges("|Z")
        .fillet(radius)
        .val()
    )
    return solid.translate((centre_x_mm, sign * (floor + end) / 2.0, 0.0))


def _stadium_window(spec: Spec, window: dict) -> cq.Solid:
    """One stadium cut through a basket wall, ends radiused to the window's height."""
    z0, z1 = spec.basket["window_z_mm"]
    height = z1 - z0
    length = window["length_mm"]
    depth = spec.wall_thickness_mm + 4 * CUT_MARGIN_MM
    radius = height / 2.0 - 0.05
    along_x = window["wall"] in ("+x", "-x")
    plane, normal = ("YZ", "|X") if along_x else ("XZ", "|Y")
    solid = (cq.Workplane(plane).rect(length, height).extrude(depth)
             .edges(normal).fillet(radius).val())
    box = solid.BoundingBox()
    solid = solid.translate((-(box.xmin + box.xmax) / 2.0,
                             -(box.ymin + box.ymax) / 2.0,
                             -(box.zmin + box.zmax) / 2.0))
    if along_x:
        sign = 1.0 if window["wall"] == "+x" else -1.0
        x = sign * (spec.wall_inner_x_mm + spec.wall_thickness_mm / 2.0)
        return solid.translate((x, window["centre_y_mm"], (z0 + z1) / 2.0))
    sign = 1.0 if window["wall"] == "+y" else -1.0
    y = sign * (spec.basket["inner_y_mm"] + spec.wall_thickness_mm / 2.0)
    return solid.translate((window["centre_x_mm"], y, (z0 + z1) / 2.0))


def build_plate(spec: Spec) -> cq.Workplane:
    """The basket: the plate, plus four walls rising to the pedal's top-face plane.

    The walls are cut from the plate's own plan so they cannot overhang the rounded
    corners, and they are 6.0 thick so the M3 pilots have 1.7 mm of PETG all round.
    """
    plan = (
        cq.Workplane("XY")
        .rect(spec.plate_x_mm, spec.plate_y_mm)
        .extrude(spec.wall_top_z_mm)
        .edges("|Z")
        .fillet(spec.corner_radius_mm)
    )
    t = spec.plate_thickness_mm
    wx0 = spec.wall_inner_x_mm
    wx1 = wx0 + spec.wall_thickness_mm
    wy0 = spec.basket["inner_y_mm"]
    wy1 = wy0 + spec.wall_thickness_mm
    walls: list[cq.Solid] = [
        _box(wx0, wx1, -spec.half_y_mm, spec.half_y_mm, t - 1, spec.wall_top_z_mm),
        _box(-wx1, -wx0, -spec.half_y_mm, spec.half_y_mm, t - 1, spec.wall_top_z_mm),
        _box(-wx0, wx0, wy0, wy1, t - 1, spec.wall_top_z_mm),
        _box(-wx0, wx0, -wy1, -wy0, t - 1, spec.wall_top_z_mm),
    ]
    body = (
        cq.Workplane("XY")
        .rect(spec.plate_x_mm, spec.plate_y_mm)
        .extrude(t)
        .edges("|Z")
        .fillet(spec.corner_radius_mm)
    )
    for wall in walls:
        body = body.union(cq.Workplane("XY").add(wall.intersect(plan.val())))

    tools: list[cq.Solid] = []
    for row in spec.clip_rows_mm:
        for centre in spec.clip_columns_mm:
            tools.append(_window_tool(spec, centre, row))
    for x in (-spec.pad_x_mm, spec.pad_x_mm):
        for y in (-spec.pad_y_mm, spec.pad_y_mm):
            tools.append(_cylinder(spec.pad_dia_mm, t - spec.pad_depth_mm,
                                   t + CUT_MARGIN_MM, x, y))
    for window in spec.basket["windows"]:
        tools.append(_stadium_window(spec, window))
    screws = spec.ring["screws"]
    for x, y in pilot_positions(spec):
        tools.append(_cylinder(screws["pilot_dia_mm"],
                               spec.wall_top_z_mm - screws["pilot_depth_mm"],
                               spec.wall_top_z_mm + CUT_MARGIN_MM, x, y))
    return _cut(body, tools).clean()


# --------------------------------------------------------------------------- #
# clips
# --------------------------------------------------------------------------- #


def _loop_section(section: Section) -> tuple[list[tuple], list[tuple]]:
    """Outer silhouette and mouth of the integral clip, in (y, z) with the post at +y.

    Taken from the J1 plate, where it reproduces the Type J1 sheet: both arms run the
    full plate thickness, the post ends inside the plate's own material, and the blade
    stands free in the window with its tip flush with the plate's top face.
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


def _extrude_loop(segments: list[tuple], width_mm: float, mirror_y: bool) -> cq.Workplane:
    first = segments[0]
    sign = -1.0 if mirror_y else 1.0
    wp = cq.Workplane("YZ").moveTo(sign * first[1], first[2])
    for seg in segments[1:]:
        if seg[0] == "L":
            wp = wp.lineTo(sign * seg[1], seg[2])
        else:
            wp = wp.threePointArc((sign * seg[3], seg[4]), (sign * seg[1], seg[2]))
    wp = wp.close().extrude(width_mm)
    box = wp.val().BoundingBox()
    return wp.translate((-(box.xmin + box.xmax) / 2.0, 0.0, 0.0))


def build_clip(spec: Spec, centre_x_mm: float, centre_y_mm: float) -> cq.Workplane:
    outer, mouth = _loop_section(spec.section)
    mirror = centre_y_mm > 0.0
    body = _extrude_loop(outer, spec.clip_width_mm, mirror)
    void = _extrude_loop(mouth, spec.clip_width_mm + CUT_MARGIN_MM * 2.0, mirror)
    return body.cut(void).translate((centre_x_mm, centre_y_mm, 0.0))


# --------------------------------------------------------------------------- #
# holders
# --------------------------------------------------------------------------- #


def _collar(spec: Spec, x: float, y: float) -> cq.Solid:
    """The pocket that hollows a cup into the ring's underside."""
    return _cylinder(
        spec.pocket_dia_mm,
        spec.collar_underside_z_mm - CUT_MARGIN_MM,
        spec.collar_underside_z_mm + spec.pocket_depth_mm,
        x, y,
    )


def build_ring(spec: Spec) -> cq.Workplane:
    """The closed top ring: one flat part that caps the walls and bears on five heads."""
    ring = spec.ring
    z0 = spec.collar_underside_z_mm
    z1 = ring["top_z_mm"]
    body = (
        cq.Workplane("XY")
        .rect(spec.plate_x_mm, spec.plate_y_mm)
        .extrude(z1 - z0)
        .edges("|Z")
        .fillet(spec.corner_radius_mm)
        .translate((0.0, 0.0, z0))
    )
    inner_xp = ring["inner_x_panel_mm"]
    inner_xt = ring["inner_x_treadle_mm"]
    tx0 = ring["treadle_column_x_mm"]
    tcy = ring["treadle_column_y_mm"]
    ly0, ly1 = ring["lip_y_mm"]

    # every side reaches inboard as a lip. The treadle column (x below the tongue
    # start) gets no end lips because the moving treadle plate covers it.
    holes: list[cq.Solid] = [
        _box(inner_xt, tx0, -tcy, tcy, z0 - 1, z1 + 1),
        _box(tx0, inner_xp, ly0, ly1, z0 - 1, z1 + 1),
    ]
    for notch in ring["notches"]:
        nx0, nx1 = notch["x_mm"]
        ny0, ny1 = notch["y_mm"]
        holes.append(_box(nx0, nx1, ny0, ny1, z0 - 1, z1 + 1))
    for site in ("A", "B", "C", "E"):
        sx, sy = spec.sites[site]
        holes.append(_collar(spec, sx, sy))
    sx, sy = spec.sites["D"]
    holes.append(_collar(spec, sx, sy))

    screws = ring["screws"]
    for x, y in pilot_positions(spec):
        holes.append(_cylinder(screws["clearance_dia_mm"], z0 - 1, z1 + 1, x, y))
        holes.append(cq.Solid.makeCone(
            screws["csk_dia_mm"] / 2.0, screws["clearance_dia_mm"] / 2.0, 2.2,
            cq.Vector(x, y, z1 + 1.0), cq.Vector(0, 0, -1)))
    return _cut(body, holes).clean()


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #


def build_treadle(spec: Spec, angle_deg: float = 0.0,
                  bounds: bool = False) -> cq.Solid:
    """The treadle as a plate on its hinge, at any angle of its travel.

    The hinge is taken at the INPUT end, so a positive angle swings the toe down. With
    ``bounds`` the plate is the conservative sweep footprint rather than the measured one:
    outboard it stops at the measured plate edge, because outboard of that is the pedal's
    own wall, and inboard it runs well past the measured edge because the rectified plan
    shows the treadle raised and in parallax.
    """
    t = spec.raw["treadle"]
    x0, x1 = t["sweep_x_mm"] if bounds else t["footprint_x_mm"]
    y0, y1 = t["sweep_y_mm"] if bounds else t["footprint_y_mm"]
    z0, z1 = t["underside_z_mm"], t["top_z_mm"]
    hy, hz = t["hinge"]["y_mm"], t["hinge"]["z_mm"]
    plate = _box(x0, x1, y0 - hy, y1 - hy, z0 - hz, z1 - hz)
    plate = plate.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), angle_deg)
    return plate.translate((0.0, hy, hz))


def treadle_sweep(spec: Spec) -> cq.Solid:
    """Everything the treadle can occupy between the ends of its travel."""
    lo, hi = spec.raw["treadle"]["sweep_deg"]
    steps = 8
    solid = cq.Workplane("XY")
    for i in range(steps + 1):
        angle = lo + (hi - lo) * i / steps
        solid = solid.union(cq.Workplane("XY").add(
            build_treadle(spec, angle, bounds=True)))
    return solid.val()


def build_pedal(spec: Spec, angle_deg: float = 0.0) -> cq.Workplane:
    """The Whammy V as an outside-only solid, for checking the fit and for renders.

    It is a checking model, not a copy of the pedal: the envelope, the top-face plane,
    the four pads, the five OEM heads and the treadle at rest - which is its highest
    position, so it is the worst case for anything the mount puts above the top face.
    Jacks are not modelled; the plan only knows their face, not where they sit.
    """
    ped = spec.raw["physical"]
    body = (
        cq.Workplane("XY")
        .rect(ped["width_mm"], ped["depth_mm"])
        .extrude(spec.pedal_top_z_mm - spec.pan_z_mm)
        .edges("|Z")
        .fillet(ped["corner_radius_mm"])
        .translate((0.0, 0.0, spec.pan_z_mm))
    )
    solid = body.union(cq.Workplane("XY").add(build_treadle(spec, angle_deg)))
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            solid = solid.union(cq.Workplane("XY").add(_cylinder(
                spec.raw["feet"]["dia_mm"], spec.pan_z_mm - spec.raw["feet"]["height_mm"],
                spec.pan_z_mm, sx * spec.raw["feet"]["x_mm"], sy * spec.raw["feet"]["y_mm"])))
    for x, y in spec.sites.values():
        solid = solid.union(cq.Workplane("XY").add(_cylinder(
            spec.head_dia_mm, spec.pedal_top_z_mm,
            spec.pedal_top_z_mm + spec.head_height_mm, x, y)))
    return solid.clean()


def clip_sites(spec: Spec) -> list[tuple[float, float]]:
    return [(cx, cy) for cy in spec.clip_rows_mm for cx in spec.clip_columns_mm]


def build(spec: Spec) -> dict[str, cq.Workplane]:
    parts = {"base": build_plate(spec), "ring": build_ring(spec)}
    mount = parts["base"]
    for cx, cy in clip_sites(spec):
        mount = mount.union(build_clip(spec, cx, cy))
    mount = mount.union(parts["ring"])
    parts["mount"] = mount.clean()
    parts["pedal"] = build_pedal(spec)
    parts["fit"] = mount.union(parts["pedal"]).clean()
    return parts


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


def _span(solid: cq.Solid, x0, x1, y0, y1, z0, z1) -> tuple[float, float, float]:
    cut = solid.intersect(_box(x0, x1, y0, y1, z0, z1))
    box = cut.BoundingBox()
    return (box.xmax - box.xmin, box.ymax - box.ymin, box.zmax - box.zmin)


def _bores(solid: cq.Solid, dia: float, tol: float = 0.05) -> list[tuple[float, float]]:
    found = []
    for face in solid.Faces():
        if face.geomType() != "CYLINDER":
            continue
        radius = BRepAdaptor_Surface(face.wrapped).Cylinder().Radius()
        if abs(2.0 * radius - dia) <= tol:
            found.append((round(face.Center().x, 2), round(face.Center().y, 2)))
    return found


def validate(spec: Spec, parts: dict[str, cq.Workplane]) -> list[Check]:
    checks: list[Check] = []

    def add(name, value, limit, ok, note=""):
        checks.append(Check(name, str(value), limit, bool(ok), note))

    basket = parts["base"].val()
    ring = parts["ring"].val()
    box = basket.BoundingBox()
    add("basket x", f"{box.xmax - box.xmin:.2f}", f"{spec.plate_x_mm:.2f}",
        abs((box.xmax - box.xmin) - spec.plate_x_mm) <= TOL_MM)
    add("basket y", f"{box.ymax - box.ymin:.2f}", f"{spec.plate_y_mm:.2f}",
        abs((box.ymax - box.ymin) - spec.plate_y_mm) <= TOL_MM)
    add("basket height", f"{box.zmax:.2f}", f"{spec.wall_top_z_mm:.2f}",
        abs(box.zmax - spec.wall_top_z_mm) <= TOL_MM)

    floor = _span(basket, -20.0, 20.0, -20.0, 20.0, -5.0, 20.0)
    add("floor thickness", f"{floor[2]:.2f}", f"{spec.plate_thickness_mm:.2f}",
        abs(floor[2] - spec.plate_thickness_mm) <= TOL_MM)
    wall = _span(basket, spec.wall_inner_x_mm - 2.0, spec.half_x_mm + 0.5,
                 22.0, 26.0, 34.0, 40.0)
    add("wall thickness", f"{wall[0]:.2f}", f"{spec.wall_thickness_mm:.2f}",
        abs(wall[0] - spec.wall_thickness_mm) <= TOL_MM)

    for name, solid in (("basket", basket), ("ring", ring)):
        add(f"{name} is one solid", len(solid.Solids()), "1", len(solid.Solids()) == 1)
        add(f"{name} watertight", solid.isValid(), "valid",
            solid.isValid() and solid.Volume() > 0)

    thickness = _span(ring, 76.0, 82.0, -40.0, -34.0, 40.0, 60.0)
    add("ring thickness", f"{thickness[2]:.2f}", f"{spec.ring_thickness_mm:.2f}",
        abs(thickness[2] - spec.ring_thickness_mm) <= TOL_MM)

    # every stadium window has to be a hole, with wall above and below it
    z0, z1 = spec.basket["window_z_mm"]
    for i, window in enumerate(spec.basket["windows"]):
        if window["wall"] in ("+x", "-x"):
            sx = 1.0 if window["wall"] == "+x" else -1.0
            cx, cy = sx * (spec.wall_inner_x_mm + 3.0), window["centre_y_mm"]
        else:
            cx = window["centre_x_mm"]
            cy = (1.0 if window["wall"] == "+y" else -1.0) * (spec.basket["inner_y_mm"] + 3.0)
        hole = basket.intersect(_box(cx - 2, cx + 2, cy - 2, cy + 2, z0 + 2, z1 - 2)).Volume()
        rail = basket.intersect(_box(cx - 2, cx + 2, cy - 2, cy + 2, 4.0, z0 - 1.0)).Volume()
        add(f"window {window['wall']}{i} open", f"{hole:.1f} mm3", "0", hole < 1.0)
        add(f"window {window['wall']}{i} rail", f"{rail:.0f} mm3", "> 20", rail > 20.0)

    found = sorted(_bores(ring, spec.pocket_dia_mm), key=lambda q: q[1])
    want = sorted((spec.sites[k] for k in ("A", "B", "C", "D", "E")), key=lambda q: q[1])
    ys_ok = all(abs(a[1] - b[1]) <= 1.0 for a, b in zip(found, want))
    add("cups", len(found), "5", len(found) == 5 and ys_ok, f"at {found}")
    add("cups cut at the treadle", len([q for q in found if q[0] < 0]), "2 (arcs)",
        len([q for q in found if q[0] < 0]) == 2)
    top = spec.collar_underside_z_mm + spec.pocket_depth_mm
    add("cup roof", f"{spec.ring['top_z_mm'] - top:.2f}", "1.20",
        abs(spec.ring["top_z_mm"] - top - 1.2) <= 0.05)
    add("cup depth", f"{spec.pocket_depth_mm:.2f}", f"{spec.head_height_mm:.2f}",
        abs(spec.pocket_depth_mm - spec.head_height_mm) <= 0.05)

    screws = spec.ring["screws"]
    add("M3 pilots", len(_bores(basket, screws["pilot_dia_mm"])), "6",
        len(_bores(basket, screws["pilot_dia_mm"])) == 6)
    add("M3 clearance", len(_bores(ring, screws["clearance_dia_mm"])), "6",
        len(_bores(ring, screws["clearance_dia_mm"])) == 6)

    probe = _box(-spec.pedal_half_x_mm + 0.1, spec.pedal_half_x_mm - 0.1,
                 -spec.pedal_half_y_mm + 0.1, spec.pedal_half_y_mm - 0.1,
                 spec.pan_z_mm + 0.1, spec.pedal_top_z_mm - 0.1)
    for name, part in (("basket", basket), ("ring", ring)):
        v = part.intersect(probe).Volume()
        add(f"{name} clear of pedal", f"{v:.3f} mm3", "0", v < 1.0)
    for zone in spec.zones:
        zx0, zx1 = zone["x_mm"]
        zy0, zy1 = zone["y_mm"]
        v = max(part.intersect(_box(zx0, zx1, zy0, zy1,
                                    spec.pedal_top_z_mm + 0.05, 60.0)).Volume()
                for part in (basket, ring))
        add(f"clear of {zone['id']}", f"{v:.3f} mm3", "0", v < 1.0)

    gap = spec.treadle_edge_x_mm - spec.treadle_cut_x_mm
    add("treadle cut clearance", f"{gap:.2f}", ">= 0.5", gap >= 0.5,
        "static: D-cut face to the treadle plate's edge")

    # the pedal has to sit in the mount with nothing in the way: any volume here is a
    # modelled clash, and coincident faces (cup roof on head top, pad on dimple floor)
    # are expected to come out at zero
    seated = parts["mount"].val().intersect(parts["pedal"].val())
    add("pedal seats in the mount", f"{seated.Volume():.1f} mm3", "< 5",
        seated.Volume() < 5.0, "modelled clash, not a tolerance sliver")

    # the treadle has to be free through its whole travel, with the plate taken wider
    # than measured, because the rectified plan shows it raised and in parallax
    swept = treadle_sweep(spec)
    for name, part in (("ring", ring), ("basket", basket)):
        v = part.intersect(swept).Volume()
        add(f"treadle sweeps clear of {name}", f"{v:.2f} mm3", "0", v < 1.0,
            "plate taken to x 12, 4.9 mm past the measured edge")
    clips_vol = 0.0
    for cx, cy in clip_sites(spec):
        clips_vol += build_clip(spec, cx, cy).val().intersect(swept).Volume()
    add("treadle sweeps clear of clips", f"{clips_vol:.2f} mm3", "0", clips_vol < 1.0)

    for cx, cy in clip_sites(spec):
        clip = build_clip(spec, cx, cy).val().BoundingBox()
        add(f"clip {cx:+.0f},{cy:+.0f} drop", f"{clip.zmin:.2f}",
            f"-{spec.section.loop_drop_mm:.2f}",
            abs(clip.zmin + spec.section.loop_drop_mm) <= 0.05)
        add(f"clip {cx:+.0f},{cy:+.0f} tip", f"{clip.zmax:.2f}",
            f"{spec.section.tip_z_mm:.2f}", abs(clip.zmax - spec.section.tip_z_mm) <= TOL_MM)
        sign = 1.0 if cy > 0 else -1.0
        end = sign * (abs(cy) + spec.section.half_outer_mm + spec.tool_gap_mm)
        rim_y = sorted((end + sign * 0.5, sign * (spec.half_y_mm - 1.0)))
        rim = basket.intersect(_box(cx - 5.0, cx + 5.0, *rim_y, -1.0, 1.0)).Volume()
        add(f"slot {cx:+.0f},{cy:+.0f} rim", f"{rim:.0f} mm3", "> 25", rim > 25.0)

    row_pitch = abs(spec.clip_rows_mm[1] - spec.clip_rows_mm[0])
    add("clip row pitch", f"{row_pitch:.1f}", "136.0 = 4 x 34", abs(row_pitch - 136.0) <= 0.2)
    col_pitch = abs(spec.clip_columns_mm[1] - spec.clip_columns_mm[0])
    add("clip column pitch", f"{col_pitch:.1f}", "76.0 = 1 x 76", abs(col_pitch - 76.0) <= 0.2)
    front = min(spec.pedal_half_y_mm - r for r in spec.clip_rows_mm)
    add("front row from corner", f"{front:.1f}", "23.0", abs(front - 23.0) <= 0.5)
    return checks


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #


def report(checks: list[Check], parts: dict[str, cq.Workplane]) -> list[str]:
    failed = [c for c in checks if not c.ok]
    lines = [f"{len(checks) - len(failed)}/{len(checks)} checks pass"]
    for c in checks:
        flag = "ok  " if c.ok else "FAIL"
        note = f"   ({c.note})" if c.note else ""
        lines.append(f"  {flag} {c.name:<24} {c.value:>12}  limit {c.limit}{note}")
    lines.append("")
    for name in ("base", "ring", "mount", "pedal"):
        vol = parts[name].val().Volume() / 1000.0
        lines.append(f"  {name:<9} {vol:6.1f} cm3   {vol * 1.27:6.1f} g in PETG")
    return lines


def summary(spec: Spec, checks: list[Check], parts: dict[str, cq.Workplane]) -> dict:
    return {
        "pedal": "DigiTech Whammy V",
        "parts_cm3": {n: round(parts[n].val().Volume() / 1000.0, 2)
                      for n in ("base", "ring", "mount")},
        "checks": {"total": len(checks), "failed": [c.name for c in checks if not c.ok]},
        "plate_mm": [spec.plate_x_mm, spec.plate_y_mm, spec.plate_thickness_mm],
        "clip_columns_mm": list(spec.clip_columns_mm),
        "clip_rows_mm": list(spec.clip_rows_mm),
        "parts": "basket + ring",
    }


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #


PART_SUFFIX = {"base": "_basket", "ring": "_ring", "mount": "",
               "pedal": "_pedal", "fit": "_in-basket"}


def export(parts: dict[str, cq.Workplane], which: list[str], fmt: str) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for name in which:
        shape = parts[name]
        stem = f"{STEM}{PART_SUFFIX[name]}"
        if fmt in ("stl", "both"):
            path = OUT / f"{stem}.stl"
            cq.exporters.export(shape, str(path), tolerance=0.02, angularTolerance=0.2)
            written.append(path)
        if fmt in ("step", "both"):
            path = OUT / f"{stem}.step"
            cq.exporters.export(shape, str(path))
            written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--part", choices=["all", "base", "ring", "mount", "pedal", "fit"],
                    default="all")
    ap.add_argument("--format", choices=["stl", "step", "both"], default="both")
    ap.add_argument("--check", action="store_true", help="run the checks and stop")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = ap.parse_args(argv)

    spec = load(args.config)
    parts = build(spec)
    checks = validate(spec, parts)

    if args.json:
        print(json.dumps(summary(spec, checks, parts), indent=2))
    else:
        for line in report(checks, parts):
            print(line)

    if any(not c.ok for c in checks):
        print("\nchecks failed; nothing written", file=sys.stderr)
        return 1
    if args.check:
        return 0

    which = (["base", "ring", "mount", "pedal", "fit"] if args.part == "all"
             else [args.part])
    for path in export(parts, which, args.format):
        print("wrote", path.relative_to(PROJECT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
