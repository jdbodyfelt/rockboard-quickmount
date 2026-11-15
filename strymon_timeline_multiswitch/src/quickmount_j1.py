"""Generate the OEM QuickMount Type J1 plate, the TimeLine half of the Strymon combo.

This is Warwick's own plate, reproduced from the Type J1 sheet in ``ref/``. That sheet
is vector and drawn at exactly 2:1, so the printed 171 x 129 outline fixes a scale for
every unprinted feature; each number the sheet prints reproduces inside 0.05 mm on that
scale, and everything comes out of ``cfg/strymon_timeline_multiswitch.json``.

The clip section is not restated here, and it is not imported from
``commons/src/retainer.py`` either: the values and the board pitch are read in from
``commons/cfg/retainer.json`` at load time, so this plate stays a self-contained module
with no cross-folder import while a corrected wall or ledge still moves every plate at
once.

What is new on this plate is the slot. The A/E plates cut a 24 mm window across their
ends and hang an inserted retainer in it; the J1 cuts the same 24 mm window in from each
long edge and makes the C-loops integral, so the post fuses into the plate's own material
at the window's inboard wall while the blade stands in the window and finishes flush with
the plate's top face.

Datum is the config's: plate bottom-face centre, +X along the 171 mm length, +Y across
the 129 mm width, +Z from the board-facing face toward the pedal.

    .venv/Scripts/python strymon_timeline_multiswitch/src/quickmount_j1.py
    .venv/Scripts/python strymon_timeline_multiswitch/src/quickmount_j1.py --part base
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT / "cfg" / "strymon_timeline_multiswitch.json"
DEFAULT_STL = PROJECT / "dwg" / "QuickMount-Type_J1.stl"
DEFAULT_BASE_STL = PROJECT / "dwg" / "QuickMount-Type_J1_base.stl"

LEN_TOL_MM = 0.02

# Slack for booleans and for the inspect-by-section probes. None of these are part
# dimensions: they only have to be big enough to clear a face and small enough not to
# change what a cut or a probe selects.
CUT_MARGIN_MM = 1.0
PROBE_STEP_MM = 0.25
PROBE_REACH_MM = 1.0
PROBE_HALF_MM = 0.5
MATCH_TOL_MM = 0.5


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Pattern:
    """One screw pattern: four holes at ±x, ±y, optionally counterbored.

    `face_side` says which face the counterbore opens on. The sheet prints its 1.5
    depth but not which way round it goes; section CC draws it on the clip side, which
    is the board-facing face, so the screw heads end up clear of the board's sheet.
    """

    id: str
    count: int
    bore_mm: float
    x_mm: float
    y_mm: float
    face_mm: float | None = None
    face_depth_mm: float = 0.0
    face_side: str = "board"

    @property
    def positions(self) -> list[tuple[float, float]]:
        if self.count == 2:
            return [(-self.x_mm, self.y_mm), (self.x_mm, self.y_mm)]
        return [
            (-self.x_mm, -self.y_mm),
            (self.x_mm, -self.y_mm),
            (-self.x_mm, self.y_mm),
            (self.x_mm, self.y_mm),
        ]


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

    # ---- where to cut a section to read a feature back --------------------- #

    @property
    def probe_mouth_z_mm(self) -> float:
        """Between the ledge and the arch springing, where the mouth is at full width."""
        return (self.ledge_z_mm + self.arch_centre_z_mm) / 2.0

    @property
    def probe_wall_z_mm(self) -> float:
        """Below the plate and above the ledge, where both walls are straight."""
        return self.ledge_z_mm / 2.0

    @property
    def probe_band_z_mm(self) -> float:
        """Just below the ledge, where the blade has stepped out to the full footprint."""
        return self.ledge_z_mm - 2.0 * PROBE_STEP_MM


@dataclass(frozen=True)
class Spec:
    raw: dict
    length_mm: float
    width_mm: float
    plate_thickness_mm: float
    corner_radius_mm: float
    notch_radius_mm: float
    slot_width_mm: float
    slot_depth_mm: float
    slot_centre_x_mm: float
    patterns: list[Pattern]
    section: Section
    clip_centre_x_mm: float
    clip_centre_y_mm: float
    clip_width_mm: float
    arch_spacing_mm: float
    clip_pitch_mm: float
    material_id: str
    density_g_cm3: float

    @property
    def half_length_mm(self) -> float:
        return self.length_mm / 2.0

    @property
    def half_width_mm(self) -> float:
        return self.width_mm / 2.0

    @property
    def slot_pitch_mm(self) -> float:
        return 2.0 * self.slot_centre_x_mm

    @property
    def slot_floor_mm(self) -> float:
        """How far in from the long edge the window stops, i.e. the clip's mouth wall."""
        return self.half_width_mm - self.slot_depth_mm

    @property
    def clip_spacing_mm(self) -> float:
        """Centre to centre across the plate, the pair that grips one rib."""
        return 2.0 * self.clip_centre_y_mm

    @property
    def clip_pitch_multiple(self) -> float:
        """How far the pair sits from a whole number of the board's pitches."""
        return self.clip_spacing_mm / self.clip_pitch_mm

    @property
    def slot_clearance_mm(self) -> float:
        """Per side, between the clip's width and the window it stands in."""
        return (self.slot_width_mm - self.clip_width_mm) / 2.0


def _read(path: Path, what: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{what} is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _section(raw: dict, plate_thickness_mm: float) -> Section:
    """The shared retainer's section, read in rather than imported."""
    env, sec = raw["envelope"], raw["section"]
    ledge = sec["ledge"]
    return Section(
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


def load(path: Path = DEFAULT_CONFIG) -> Spec:
    raw = _read(path, path.name)
    mount = raw["quickmount"]
    plate = mount["plate"]
    windows = mount["windows"]
    clips = mount["clips"]
    holes = mount["holes"]
    thickness = float(plate["thickness_mm"])

    def pattern(key: str) -> Pattern:
        node = holes[key]
        face_key = "counterbore_mm"
        side = str(node.get("counterbore_face", "board"))
        if side not in ("pedal", "board"):
            raise ValueError(
                f"{path.name}: {key} counterbore_face must be pedal or board, not {side!r}"
            )
        return Pattern(
            id=key,
            count=int(node["count"]),
            bore_mm=float(node["bore_mm"]),
            x_mm=float(node["x_mm"]),
            y_mm=float(node["y_mm"]),
            face_mm=float(node[face_key]) if face_key in node else None,
            face_depth_mm=float(node.get("counterbore_depth_mm", 0.0)),
            face_side=side,
        )

    section_raw = _read(PROJECT / clips["section"], f"{path.name}: clip section")
    pitch = section_raw.get("array", {}).get("pair_pitch_mm")
    if not pitch:
        raise KeyError(
            f"{clips['section']}: array.pair_pitch_mm has to be set for the pitch check"
        )

    material = raw["material"]
    presets_path = PROJECT / material["presets_from"]
    presets = _read(presets_path, f"{path.name}: material presets")["material"][
        "presets"
    ]
    material_id = str(material["id"])
    if material_id not in presets:
        raise KeyError(
            f"{material['presets_from']}: no preset for material {material_id!r}"
        )

    section = _section(section_raw, thickness)
    clip_width = float(clips["width_along_x_mm"])
    if abs(clip_width - section.width_along_slot_mm) > LEN_TOL_MM:
        raise ValueError(
            f"{path.name}: clips.width_along_x_mm is {clip_width:g} but "
            f"{clips['section']} gives {section.width_along_slot_mm:g}"
        )

    return Spec(
        raw=raw,
        length_mm=float(plate["length_mm"]),
        width_mm=float(plate["width_mm"]),
        plate_thickness_mm=thickness,
        corner_radius_mm=float(plate["corner_radius_mm"]),
        notch_radius_mm=float(plate["notch_corner_radius_mm"]),
        slot_width_mm=float(windows["width_mm"]),
        slot_depth_mm=float(windows["depth_mm"]),
        slot_centre_x_mm=float(windows["centre_x_mm"]),
        patterns=[pattern("clearance"), pattern("boss"), pattern("mid")],
        section=section,
        clip_centre_x_mm=float(clips["centre_x_mm"]),
        clip_centre_y_mm=float(clips["centre_y_mm"]),
        clip_width_mm=clip_width,
        arch_spacing_mm=float(clips["arch_spacing_mm"]),
        clip_pitch_mm=float(pitch),
        material_id=material_id,
        density_g_cm3=float(presets[material_id]["density_g_cm3"]),
    )


# --------------------------------------------------------------------------- #
# geometry helpers
# --------------------------------------------------------------------------- #


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> cq.Solid:
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def _cylinder(dia: float, z0: float, z1: float, x: float, y: float) -> cq.Solid:
    return cq.Solid.makeCylinder(
        dia / 2.0, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1)
    )


def _cut(wp: cq.Workplane, tools: list[cq.Solid]) -> cq.Workplane:
    if not tools:
        return wp
    stack = cq.Workplane("XY")
    for tool in tools:
        stack = stack.add(tool)
    return wp.cut(stack)


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #


def outline_profile(spec: Spec) -> cq.Workplane:
    """The plate silhouette: 171 x 129 with R3 corners."""
    return (
        cq.Workplane("XY")
        .rect(spec.length_mm, spec.width_mm)
        .extrude(spec.plate_thickness_mm)
        .edges("|Z")
        .fillet(spec.corner_radius_mm)
    )


def _slot_tool(spec: Spec, centre_x_mm: float, sign: float) -> cq.Workplane:
    """One window, cut through the plate from a long edge.

    All four corners keep R1, as the sheet draws them: the floor between the clip's
    arch and the mouth where the wall meets the plate's edge. The mouth fillets are why
    the drawn edge line stops a millimetre inboard of each wall.
    """
    half = spec.slot_width_mm / 2.0
    radius = spec.notch_radius_mm
    edge = spec.half_width_mm
    out = edge + CUT_MARGIN_MM
    floor = spec.slot_floor_mm
    corner = radius - radius / math.sqrt(2.0)

    def at(x: float, y: float) -> tuple[float, float]:
        return (centre_x_mm + x, sign * y)

    wp = cq.Workplane("XY").moveTo(*at(-half - radius, out))
    wp = wp.lineTo(*at(-half - radius, edge))
    wp = wp.threePointArc(at(-half - corner, edge - corner), at(-half, edge - radius))
    wp = wp.lineTo(*at(-half, floor + radius))
    wp = wp.threePointArc(at(-half + corner, floor + corner), at(-half + radius, floor))
    wp = wp.lineTo(*at(half - radius, floor))
    wp = wp.threePointArc(at(half - corner, floor + corner), at(half, floor + radius))
    wp = wp.lineTo(*at(half, edge - radius))
    wp = wp.threePointArc(at(half + corner, edge - corner), at(half + radius, edge))
    wp = wp.lineTo(*at(half + radius, out))
    return wp.close().extrude(spec.plate_thickness_mm)


def build_base(spec: Spec) -> cq.Workplane:
    plate = outline_profile(spec)
    thickness = spec.plate_thickness_mm
    tools: list[cq.Solid] = []

    for sign in (-1.0, 1.0):
        for centre in (-spec.slot_centre_x_mm, spec.slot_centre_x_mm):
            tools.append(_slot_tool(spec, centre, sign).val())

    for pattern in spec.patterns:
        for x, y in pattern.positions:
            tools.append(
                _cylinder(
                    pattern.bore_mm, -CUT_MARGIN_MM, thickness + CUT_MARGIN_MM, x, y
                )
            )
            if pattern.face_mm and pattern.face_depth_mm:
                if pattern.face_side == "board":
                    z0, z1 = -CUT_MARGIN_MM, pattern.face_depth_mm
                else:
                    z0, z1 = (
                        thickness - pattern.face_depth_mm,
                        thickness + CUT_MARGIN_MM,
                    )
                tools.append(_cylinder(pattern.face_mm, z0, z1, x, y))

    return _cut(plate, tools)


def _loop_section(section: Section) -> tuple[list[tuple], list[tuple]]:
    """Outer silhouette and mouth for the integral clip, in (y, z) with the post at +y.

    Both arms run the full plate thickness. The post ends up inside the plate's own
    material and fuses to it; the blade stands in the window with clearance all round,
    so its tip finishes flush with the plate's top face and is still free to flex the
    ledge under the board's sheet. The mouth therefore stays open through the plate,
    exactly as it does on a plate that takes an inserted retainer.
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


def _extrude_loop(
    segments: list[tuple], width_mm: float, mirror_y: bool
) -> cq.Workplane:
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
    """One integral C-loop standing in its window.

    The blade - the arm carrying the ledge - points outboard, toward the long edge, so
    the pair grips the same rib from either side, and the mouth faces the plate's centre
    line. That leaves the post inboard of the mouth, inside the plate's own material, and
    the blade inside the window.
    """
    outer, mouth = _loop_section(spec.section)
    mirror = centre_y_mm > 0.0
    body = _extrude_loop(outer, spec.clip_width_mm, mirror)
    void = _extrude_loop(mouth, spec.clip_width_mm + CUT_MARGIN_MM * 2.0, mirror)
    clip = body.cut(void)
    return clip.translate((centre_x_mm, centre_y_mm, 0.0))


def build(spec: Spec) -> tuple[cq.Workplane, cq.Workplane]:
    base = build_base(spec)
    mount = base
    for sign_y in (-1.0, 1.0):
        for sign_x in (-1.0, 1.0):
            mount = mount.union(
                build_clip(
                    spec, sign_x * spec.clip_centre_x_mm, sign_y * spec.clip_centre_y_mm
                )
            )
    return mount.clean(), base.clean()


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


def _pieces(solid: cq.Solid, x0, x1, y0, y1, z0, z1, sort: str = "xmin") -> list:
    cut = solid.intersect(_box(x0, x1, y0, y1, z0, z1))
    boxes = [s.BoundingBox() for s in cut.Solids()]
    return sorted(boxes, key=lambda b: getattr(b, sort))


def _bore_faces(solid: cq.Solid, dia: float, tol: float = 0.01) -> list:
    faces = []
    for face in solid.Faces():
        if face.geomType() != "CYLINDER":
            continue
        radius = face._geomAdaptor().Cylinder().Radius()
        if abs(2.0 * radius - dia) <= tol:
            faces.append(face)
    return faces


def _bores(solid: cq.Solid, dia: float, tol: float = 0.01) -> list[tuple[float, float]]:
    return [(f.Center().x, f.Center().y) for f in _bore_faces(solid, dia, tol)]


def _bores_at(solid: cq.Solid, dia: float, y_mm: float) -> list[tuple[float, float]]:
    """Bores of that diameter on the row at ±|y|, so the two Ø3.5 patterns stay apart."""
    return [
        (x, y) for x, y in _bores(solid, dia) if abs(abs(y) - abs(y_mm)) < MATCH_TOL_MM
    ]


def _pitch(values: list[float]) -> float:
    return max(values) - min(values)


# Names of the mount checks that a bare plate also has to pass, so --part base is
# gated on the same numbers as the finished plate.
PLATE_CHECK_NAMES = {
    "overall length",
    "overall width",
    "plate thickness",
    "corner radius",
    "slot width",
    "slot depth",
    "slot pitch",
}


def validate(spec: Spec, mount: cq.Workplane, base: cq.Workplane) -> list[Check]:
    solid = mount.val()
    plate = base.val()
    box = solid.BoundingBox()
    plate_box = plate.BoundingBox()
    sec = spec.section
    checks: list[Check] = []

    # Every probe below is placed from the config and the shared section, so a
    # corrected number moves the check with the geometry instead of past it.
    x0, x1 = plate_box.xmin - PROBE_REACH_MM, plate_box.xmax + PROBE_REACH_MM
    y0, y1 = plate_box.ymin - PROBE_REACH_MM, plate_box.ymax + PROBE_REACH_MM
    mid_z = spec.plate_thickness_mm / 2.0
    clip_x = spec.clip_centre_x_mm
    clip_y = spec.clip_centre_y_mm
    near_x = (
        clip_x - spec.clip_width_mm / 2.0 - PROBE_REACH_MM,
        clip_x + spec.clip_width_mm / 2.0 + PROBE_REACH_MM,
    )
    outboard_y = (clip_y - sec.half_outer_mm - PROBE_REACH_MM, y1)

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

    exact(
        "overall length",
        box.xlen,
        spec.length_mm,
        "171.0 on the top and bottom views",
    )
    exact("overall width", box.ylen, spec.width_mm, "129.0 on both views")
    exact(
        "plate thickness",
        plate_box.zlen,
        spec.plate_thickness_mm,
        "3 printed on section CC",
    )

    corner = _pieces(
        plate,
        spec.half_length_mm - PROBE_STEP_MM,
        x1,
        spec.half_width_mm - PROBE_STEP_MM,
        y1,
        mid_z - PROBE_STEP_MM,
        mid_z + PROBE_STEP_MM,
    )
    flag(
        "corner radius",
        f"{len(corner)} solids",
        "0",
        not corner,
        f"R{spec.corner_radius_mm:g} relief at all four outline corners",
    )

    floor = spec.slot_floor_mm
    row = _pieces(
        plate,
        x0,
        x1,
        floor + spec.notch_radius_mm + PROBE_STEP_MM,
        spec.half_width_mm - PROBE_STEP_MM,
        mid_z - PROBE_STEP_MM,
        mid_z + PROBE_STEP_MM,
    )
    flag(
        "slots per edge",
        f"{len(row) - 1}",
        "2",
        len(row) == 3,
        "two windows cut in from each long edge, so three bands of plate remain",
    )
    if len(row) == 3:
        exact(
            "slot width",
            row[1].xmin - row[0].xmax,
            spec.slot_width_mm,
            "24, printed on the top view",
        )
        exact(
            "slot width, other side",
            row[2].xmin - row[1].xmax,
            spec.slot_width_mm,
            "the pair has to match",
        )
        centres = [
            (row[0].xmax + row[1].xmin) / 2.0,
            (row[1].xmax + row[2].xmin) / 2.0,
        ]
        exact(
            "slot pitch",
            _pitch(centres),
            spec.slot_pitch_mm,
            "76.00, the printed 24 slot and 52 gap",
        )

    strip = _pieces(
        plate,
        clip_x - PROBE_HALF_MM,
        clip_x + PROBE_HALF_MM,
        floor - PROBE_REACH_MM,
        y1,
        mid_z - PROBE_STEP_MM,
        mid_z + PROBE_STEP_MM,
    )[0]
    exact(
        "slot depth",
        spec.half_width_mm - strip.ymax,
        spec.slot_depth_mm,
        "the mouth carried out to the long edge",
    )
    flag(
        "window lands on the mouth",
        f"{floor:.2f} mm",
        f"{clip_y - sec.half_mouth_mm:.2f} mm",
        abs(floor - (clip_y - sec.half_mouth_mm)) <= 0.3,
        "the window's floor is the clip's mouth wall, so the plate cannot close the loop",
    )
    cavity = _pieces(
        solid,
        clip_x - PROBE_HALF_MM,
        clip_x + PROBE_HALF_MM,
        clip_y - sec.half_mouth_mm,
        clip_y,
        mid_z - PROBE_STEP_MM,
        mid_z + PROBE_STEP_MM,
    )
    flag(
        "mouth open through the plate",
        f"{len(cavity)} solids",
        "0",
        not cavity,
        "nothing of the plate sits over the mouth",
    )

    blade_y = (clip_y + sec.half_mouth_mm + PROBE_STEP_MM, clip_y + sec.half_outer_mm)
    blade = _pieces(
        solid,
        clip_x - PROBE_HALF_MM * 2.0,
        clip_x + PROBE_HALF_MM * 2.0,
        blade_y[0],
        blade_y[1] - PROBE_STEP_MM,
        mid_z,
        spec.plate_thickness_mm + PROBE_REACH_MM,
    )
    flag(
        "blade through the window",
        f"{len(blade)} solids",
        "1",
        len(blade) == 1,
        "the tip passes up the window on its own, clear of the plate",
    )
    exact(
        "blade tip flush with the plate top",
        blade[0].zmax if blade else float("nan"),
        spec.plate_thickness_mm,
        "the lip finishes level with the plate's top face",
    )
    around = _pieces(
        solid,
        clip_x - spec.slot_width_mm / 2.0,
        clip_x + spec.slot_width_mm / 2.0,
        blade_y[0],
        blade_y[1] - PROBE_STEP_MM,
        spec.plate_thickness_mm - PROBE_STEP_MM,
        spec.plate_thickness_mm - PROBE_STEP_MM * 0.5,
    )
    exact(
        "blade width in the window",
        (around[0].xmax - around[0].xmin) if len(around) == 1 else float("nan"),
        spec.clip_width_mm,
        f"{spec.clip_width_mm:g} across a {spec.slot_width_mm:g} window, so "
        f"{spec.slot_clearance_mm:.2f} clear a side",
    )

    band = (sec.probe_band_z_mm - PROBE_STEP_MM, sec.probe_band_z_mm)
    inset = (sec.ledge_z_mm + PROBE_STEP_MM, sec.ledge_z_mm + 2.0 * PROBE_STEP_MM)
    foot = (
        -sec.loop_drop_mm + 2.0 * PROBE_STEP_MM,
        -sec.loop_drop_mm + 3.0 * PROBE_STEP_MM,
    )

    def merged(pieces) -> tuple[float, float, float, float]:
        """Outer x and y span of a clip probed as separate walls."""
        return (
            min(p.xmin for p in pieces),
            max(p.xmax for p in pieces),
            min(p.ymin for p in pieces),
            max(p.ymax for p in pieces),
        )

    # Near the arch's bottom the section is one closed loop per clip; above the arch
    # springing it is two separate walls, which is why the spans below merge.
    clips = _pieces(solid, x0, x1, y0, y1, *foot)
    flag(
        "clip count",
        str(len(clips)),
        "4",
        len(clips) == 4,
        "one in each window",
    )
    if len(clips) == 4:
        exact(
            "clip width along x",
            max(p.xlen for p in clips),
            spec.clip_width_mm,
            "22, printed on the A/E sheets",
        )
    spread = _pieces(solid, x0, x1, y0, y1, *band)
    if spread:
        exact(
            "clip arch spacing",
            merged(spread)[3] - merged(spread)[2],
            spec.arch_spacing_mm,
            "111.7, printed on section BB, so the centres sit at ±46.35",
        )
        exact(
            "clip centre across",
            (merged(spread)[2] + merged(spread)[3]) / 2.0,
            0.0,
            "the four clips are symmetric about the plate's centre line",
        )
    single = _pieces(solid, near_x[0], near_x[1], *outboard_y, *band)
    inset_pieces = _pieces(solid, near_x[0], near_x[1], *outboard_y, *inset)
    exact(
        "clip outer width",
        merged(single)[3] - merged(single)[2] if single else float("nan"),
        sec.outer_width_mm,
        "19.0 in the retainer section",
    )
    exact(
        "clip drop below the plate",
        -box.zmin,
        sec.loop_drop_mm,
        "the retainer's 15.89 below the underside",
    )

    ledges = [
        f
        for f in solid.Faces()
        if f.geomType() == "PLANE"
        and f.normalAt().z > 0.999
        and -sec.loop_drop_mm + PROBE_STEP_MM < f.Center().z < -PROBE_STEP_MM
    ]
    flag(
        "ledge faces",
        str(len(ledges)),
        "4",
        len(ledges) == 4,
        "one upward face per clip, the one that catches the sheet",
    )
    if ledges:
        exact(
            "ledge drop",
            abs(ledges[0].Center().z),
            sec.ledge_drop_mm,
            "4.00 below the plate underside",
        )

    mouth = _pieces(
        solid,
        near_x[0],
        near_x[1],
        *outboard_y,
        sec.probe_mouth_z_mm - PROBE_STEP_MM,
        sec.probe_mouth_z_mm,
        sort="ymin",
    )
    exact(
        "clip mouth",
        mouth[-1].ymin - mouth[0].ymax if len(mouth) == 2 else float("nan"),
        sec.mouth_width_mm,
        "13.0, the retainer's mouth, measured above the arch springing",
    )
    walls = _pieces(
        solid,
        near_x[0],
        near_x[1],
        *outboard_y,
        sec.probe_wall_z_mm - PROBE_STEP_MM,
        sec.probe_wall_z_mm,
        sort="ymin",
    )
    if len(walls) == 2:
        exact(
            "clip post wall",
            walls[0].ylen,
            sec.post_wall_mm,
            "3.00, the rigid side of the loop, fused into the plate",
        )
        exact(
            "clip blade wall",
            walls[1].ylen,
            sec.blade_wall_mm,
            "1.90, the side that has to flex",
        )
    exact(
        "ledge protrusion",
        (merged(single)[3] - merged(inset_pieces)[3])
        if single and inset_pieces
        else float("nan"),
        sec.ledge_protrusion_mm,
        "1.10 outboard, under the sheet: the blade is inset above the ledge so the sheet edge can pass",
    )

    for pattern in spec.patterns:
        bores = _bores_at(solid, pattern.bore_mm, pattern.y_mm)
        flag(
            f"{pattern.id} holes",
            str(len(bores)),
            str(pattern.count),
            len(bores) == pattern.count,
            f"Ø{pattern.bore_mm:g}",
        )
        xs = [x for x, _ in bores] or [0.0]
        ys = [y for _, y in bores] or [0.0]
        exact(f"{pattern.id} pitch across", _pitch(xs), 2.0 * pattern.x_mm)
        if pattern.count == 4:
            exact(f"{pattern.id} pitch along", _pitch(ys), 2.0 * pattern.y_mm)
        if pattern.face_mm:
            faces = _bores_at(solid, pattern.face_mm, pattern.y_mm)
            flag(
                f"{pattern.id} counterbores",
                str(len(faces)),
                str(pattern.count),
                len(faces) == pattern.count,
                f"Ø{pattern.face_mm:g} x {pattern.face_depth_mm:g} deep, {pattern.face_side} side",
            )
            want = (
                spec.plate_thickness_mm - pattern.face_depth_mm / 2.0
                if pattern.face_side == "pedal"
                else pattern.face_depth_mm / 2.0
            )
            zs = [
                f.Center().z
                for f in _bore_faces(solid, pattern.face_mm)
                if abs(abs(f.Center().y) - abs(pattern.y_mm)) < MATCH_TOL_MM
            ]
            worst = max((abs(z - want) for z in zs), default=float("nan"))
            flag(
                f"{pattern.id} face side",
                f"{sum(zs) / len(zs):.2f} mm" if zs else "-",
                f"{want:.2f} mm",
                worst <= LEN_TOL_MM,
                f"counterbore centre has to sit on the {pattern.face_side} side",
            )

    flag(
        "solid count",
        str(len(solid.Solids())),
        "1",
        len(solid.Solids()) == 1,
        "plate and clips have to fuse",
    )
    mass = solid.Volume() / 1000.0 * spec.density_g_cm3
    flag(
        "volume",
        f"{solid.Volume():.0f} mm3",
        "> 0",
        solid.Volume() > 0.0,
        f"{mass:.1f} g in {spec.material_id}",
    )
    return checks


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #


def report(spec: Spec, checks: list[Check], out: Path) -> str:
    sec = spec.section
    lines = [
        f"Strymon combo, QuickMount Type J1  ({Path(out).name})",
        "",
        "plate, from the Type J1 sheet at its own 2:1 scale",
        f"  length                {spec.length_mm:7.2f} mm   171, both views",
        f"  width                 {spec.width_mm:7.2f} mm   129, both views",
        f"  thickness             {spec.plate_thickness_mm:7.2f} mm   3, section CC",
        f"  corner radius         {spec.corner_radius_mm:7.2f} mm   R3 on the top view",
        (
            f"  windows               4 x {spec.slot_width_mm:.2f} x "
            f"{spec.slot_depth_mm:.2f} mm, open to the long edges, "
            f"R{spec.notch_radius_mm:g} on all four corners"
        ),
        f"  window centres        ±{spec.slot_centre_x_mm:.2f} mm, {spec.slot_pitch_mm:.2f} apart",
        f"  window leaves         {spec.slot_clearance_mm:.2f} mm clear of the clip each side",
        "",
        "screws",
    ]
    for pattern in spec.patterns:
        face = (
            f", Ø{pattern.face_mm:g} counterbore {pattern.face_depth_mm:g} deep on the "
            f"{pattern.face_side} side"
            if pattern.face_mm
            else ""
        )
        lines.append(
            f"  {pattern.id:<10} {pattern.count:2d} x Ø{pattern.bore_mm:g} at "
            f"({pattern.x_mm:.2f}, {pattern.y_mm:.2f}){face}"
        )
    lines += [
        "",
        "clips, the shared retainer section with integral arms",
        f"  width along x         {spec.clip_width_mm:7.2f} mm   22, printed on the A/E sheets",
        f"  outer width           {sec.outer_width_mm:7.2f} mm",
        f"  mouth                 {sec.mouth_width_mm:7.2f} mm",
        (
            f"  drop below the plate  {sec.loop_drop_mm:7.2f} mm   total "
            f"{sec.drop_below_plate_top_mm:.2f} from the plate top"
        ),
        (
            f"  tip                   flush with the plate's "
            f"{spec.plate_thickness_mm:.2f} top face, through the window"
        ),
        (
            f"  ledge                 {sec.ledge_protrusion_mm:.2f} mm out at "
            f"{sec.ledge_drop_mm:.2f} below the underside"
        ),
        (
            f"  centres               (±{spec.clip_centre_x_mm:.2f}, "
            f"±{spec.clip_centre_y_mm:.2f}) mm, "
            f"{spec.clip_spacing_mm:.2f} apart across the plate"
        ),
        f"  arch spacing          {spec.arch_spacing_mm:7.2f} mm   printed on section BB",
        (
            f"    against the board    {spec.clip_pitch_multiple:.2f} of the "
            f"{spec.clip_pitch_mm:.2f} pitch, so not rib-centred"
            if abs(spec.clip_pitch_multiple - round(spec.clip_pitch_multiple)) > 0.05
            else f"    against the board    a whole {round(spec.clip_pitch_multiple)} of the "
            f"{spec.clip_pitch_mm:.2f} pitch, so rib-centred"
        ),
        "",
        "checks",
    ]
    width = max(len(c.name) for c in checks)
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        lines.append(
            f"  {mark} {c.name:<{width}}  {c.value:>12}  {c.limit:>12}  {c.note}"
        )
    failed = [c for c in checks if not c.ok]
    lines.append("")
    lines.append(
        f"{len(checks) - len(failed)}/{len(checks)} checks pass"
        if not failed
        else f"{len(failed)} CHECK(S) FAILED"
    )

    verification = spec.raw["quickmount"].get("verification", {})
    if verification.get("cross_checks"):
        lines += ["", "verified against the drawing sheet"]
        for item in verification["cross_checks"]:
            lines.append(f"  {item['value']:<44} {item['verdict']}")
    return "\n".join(lines)


def summary(spec: Spec, checks: list[Check], out: Path) -> dict:
    return {
        "id": spec.raw["quickmount"]["id"],
        "stl": str(out),
        "plate_mm": {
            "length": spec.length_mm,
            "width": spec.width_mm,
            "thickness": spec.plate_thickness_mm,
            "corner_radius": spec.corner_radius_mm,
            "slot": [spec.slot_width_mm, spec.slot_depth_mm],
            "slot_pitch": spec.slot_pitch_mm,
        },
        "screw_patterns": {
            p.id: {
                "count": p.count,
                "bore": p.bore_mm,
                "x": p.x_mm,
                "y": p.y_mm,
                "counterbore": p.face_mm,
                "face": p.face_side,
            }
            for p in spec.patterns
        },
        "clips": {
            "count": 4,
            "centre_x": spec.clip_centre_x_mm,
            "centre_y": spec.clip_centre_y_mm,
            "spacing": spec.clip_spacing_mm,
            "arch_spacing": spec.arch_spacing_mm,
            "pitch_multiple": spec.clip_pitch_multiple,
            "width": spec.clip_width_mm,
            "drop_below_plate": spec.section.loop_drop_mm,
        },
        "checks": [
            {"name": c.name, "value": c.value, "limit": c.limit, "ok": c.ok}
            for c in checks
        ],
        "ok": all(c.ok for c in checks),
    }


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument(
        "--part",
        choices=("mount", "base"),
        default="mount",
        help="mount is the plate with its clips; base is the bare plate, for a riser",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="STL to write, instead of the default name",
    )
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    ap.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="mesh deflection in mm, for the STL only",
    )
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    spec = load(args.config)
    mount, base = build(spec)
    checks = validate(spec, mount, base)

    if args.part == "base":
        part = base
        out = args.out or DEFAULT_BASE_STL
        part_checks = [c for c in checks if c.name in PLATE_CHECK_NAMES]
        for pattern in spec.patterns:
            part_checks += [c for c in checks if c.name.startswith(f"{pattern.id} ")]
        part_checks.append(
            Check(
                "resting face flat",
                f"{base.val().BoundingBox().zmax:.2f} mm",
                f"{spec.plate_thickness_mm:.2f} mm",
                abs(base.val().BoundingBox().zmax - spec.plate_thickness_mm)
                <= LEN_TOL_MM,
                "the bare plate has to hand the riser a flat face",
            )
        )
    else:
        part = mount
        out = args.out or DEFAULT_STL
        part_checks = checks

    ok = all(c.ok for c in part_checks)
    out.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(part, str(out), tolerance=args.tolerance, angularTolerance=0.1)
    cq.exporters.export(part, str(out.with_suffix(".step")))
    if args.json:
        print(json.dumps(summary(spec, part_checks, out), indent=2))
    else:
        print(report(spec, part_checks, out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
