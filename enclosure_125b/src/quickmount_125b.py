"""Generate the OEM QuickMount Type B1 plate for a vertical 125B housing.

This is Warwick's own plate, reproduced from the two Type B1 sheets in ``ref/``
rather than from the third-party mesh kept beside the output. Every printed
callout comes out of ``cfg/enclosure_125b.json``; the features neither sheet
prints were scaled off the vector alt sheet at its own callouts and are recorded,
with that 0.3 mm uncertainty, in the same file.

The clip section is deliberately not restated here, and it is not imported from
``commons/src/retainer.py`` either: the values and the board pitch are read in from
``commons/cfg/retainer.json`` at load time, so this plate stays a self-contained
module with no cross-folder import while a corrected wall or ledge still moves every
plate at once. What is new on this plate is that the C-loops are integral: their arms
stop inside the 3 mm plate instead of passing through a slot.

Datum is the config's: plate bottom-face centre, +X across the width, +Y along
the length, +Z from the board-facing face toward the pedal.

    .venv/Scripts/python enclosure_125b/src/quickmount_125b.py
    .venv/Scripts/python enclosure_125b/src/quickmount_125b.py --part base
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
DEFAULT_CONFIG = PROJECT / "cfg" / "enclosure_125b.json"
DEFAULT_STL = PROJECT / "dwg" / "125B_quickmount.stl"
DEFAULT_BASE_STL = PROJECT / "dwg" / "125B_quickmount_base.stl"
DEFAULT_CLIP_STL = PROJECT / "dwg" / "125B_clip.stl"

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

    `face_side` says which face the counterbore or spot-face opens on, because the
    drawing only prints its 1.5 depth, not which way round it goes.
    """

    id: str
    count: int
    bore_mm: float
    x_mm: float
    y_mm: float
    face_mm: float | None = None
    face_depth_mm: float = 0.0
    face_side: str = "pedal"

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
    side_width_mm: float
    width_mm: float
    lobe_radius_mm: float
    lobe_x_mm: float
    lobe_y_mm: float
    boss_radius_mm: float
    boss_x_mm: float
    boss_y_mm: float
    window_width_mm: float
    window_depth_mm: float
    plate_thickness_mm: float
    patterns: list[Pattern]
    section: Section
    clip_pitch_mm: float
    clip_centre_y_mm: float
    oem_slits: list[tuple[float, float]]
    oem_fingers_mm: list[float]
    oem_reference: Path
    material_id: str
    density_g_cm3: float

    @property
    def half_length_mm(self) -> float:
        return self.length_mm / 2.0

    @property
    def half_side_mm(self) -> float:
        return self.side_width_mm / 2.0

    @property
    def clip_spacing_mm(self) -> float:
        return 2.0 * self.clip_centre_y_mm

    @property
    def clip_pitch_multiple(self) -> float:
        """How far the pair sits from a whole number of the board's pitches."""
        return self.clip_spacing_mm / self.clip_pitch_mm

    @property
    def side_edge_top_mm(self) -> float:
        """Where a corner lobe crosses the straight side, so the side edge starts."""
        dx = self.half_side_mm - self.lobe_x_mm
        return self.lobe_y_mm - math.sqrt(self.lobe_radius_mm**2 - dx**2)

    @property
    def boss_edge_mm(self) -> float:
        dx = self.half_side_mm - self.boss_x_mm
        return math.sqrt(self.boss_radius_mm**2 - dx**2)


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


def _oem_slits(variant: dict) -> tuple[list[tuple[float, float]], list[float]]:
    """Where Warwick's finger relief sits, as x ranges across the clip's width.

    The fingers are laid out about the clip's centre, each slit cut between them, so
    the set closes on the 22 mm the clip uses.
    """
    fingers = [float(v) for v in variant["finger_widths_mm"]]
    slit = float(variant["slit_width_mm"])
    total = sum(fingers) + slit * (len(fingers) - 1)
    x = -total / 2.0
    ranges: list[tuple[float, float]] = []
    for index, width in enumerate(fingers):
        x += width
        if index < len(fingers) - 1:
            ranges.append((x, x + slit))
            x += slit
    return ranges, fingers


def load(path: Path = DEFAULT_CONFIG) -> Spec:
    raw = _read(path, path.name)
    mount = raw["mount"]
    outline = mount["outline"]
    holes = mount["holes"]
    clips = mount["clips"]
    thickness = float(mount["plate_thickness_mm"])

    def pattern(key: str, face_key: str) -> Pattern:
        node = holes[key]
        side = str(node.get(face_key.replace("_mm", "_face"), "pedal"))
        if side not in ("pedal", "board"):
            raise ValueError(
                f"{path.name}: {key} {face_key} face must be pedal or board, not {side!r}"
            )
        return Pattern(
            id=key,
            count=int(node["count"]),
            bore_mm=float(node["bore_mm"]),
            x_mm=float(node["x_mm"]),
            y_mm=float(node["y_mm"]),
            face_mm=float(node[face_key]) if face_key in node else None,
            face_depth_mm=float(
                node.get("counterbore_depth_mm", node.get("spotface_depth_mm", 0.0))
            ),
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

    variant = clips["oem_variant"]
    oem_slits, oem_fingers = _oem_slits(variant)
    oem_reference = PROJECT / variant["reference_mesh"]

    return Spec(
        raw=raw,
        length_mm=float(outline["length_mm"]),
        side_width_mm=float(outline["side_width_mm"]),
        width_mm=float(outline["width_over_lobes_mm"]),
        lobe_radius_mm=float(outline["corner_lobe_radius_mm"]),
        lobe_x_mm=float(outline["corner_lobe_x_mm"]),
        lobe_y_mm=float(outline["corner_lobe_y_mm"]),
        boss_radius_mm=float(outline["side_boss_radius_mm"]),
        boss_x_mm=float(holes["side"]["x_mm"]),
        boss_y_mm=float(holes["side"]["y_mm"]),
        window_width_mm=float(outline["end_window"]["width_mm"]),
        window_depth_mm=float(outline["end_window"]["depth_mm"]),
        plate_thickness_mm=thickness,
        patterns=[
            pattern("clearance", "counterbore_mm"),
            pattern("snap", "spotface_mm"),
            pattern("side", "spotface_mm"),
        ],
        section=_section(section_raw, thickness),
        clip_pitch_mm=float(pitch),
        clip_centre_y_mm=float(clips["centre_y_mm"]),
        oem_slits=oem_slits,
        oem_fingers_mm=oem_fingers,
        oem_reference=oem_reference,
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
    """The plate silhouette: straight sides, four lobes and the two side bosses.

    Every arc is centred on the feature it protects - a lobe on its snap hole, a
    boss on its side hole - which is what makes the 67 mm sides and the 72 mm
    over the lobes close against the printed 125.5 mm.
    """
    hx, hy = spec.half_side_mm, spec.half_length_mm
    lx, ly, lr = spec.lobe_x_mm, spec.lobe_y_mm, spec.lobe_radius_mm
    top = spec.side_edge_top_mm
    boss = spec.boss_edge_mm
    bx, by, br = spec.boss_x_mm, spec.boss_y_mm, spec.boss_radius_mm

    wp = cq.Workplane("XY").moveTo(0.0, hy)
    wp = wp.lineTo(lx, hy)
    wp = wp.threePointArc((lx + lr, ly), (hx, top))
    wp = wp.lineTo(hx, by + boss)
    wp = wp.threePointArc((bx + br, by), (hx, by - boss))
    wp = wp.lineTo(hx, -top)
    wp = wp.threePointArc((lx + lr, -ly), (lx, -hy))
    wp = wp.lineTo(-lx, -hy)
    wp = wp.threePointArc((-lx - lr, -ly), (-hx, -top))
    wp = wp.lineTo(-hx, by - boss)
    wp = wp.threePointArc((-bx - br, by), (-hx, by + boss))
    wp = wp.lineTo(-hx, top)
    wp = wp.threePointArc((-lx - lr, ly), (-lx, hy))
    return wp.close()


def build_base(spec: Spec) -> cq.Workplane:
    plate = outline_profile(spec).extrude(spec.plate_thickness_mm)
    thickness = spec.plate_thickness_mm

    tools: list[cq.Solid] = []

    half_window = spec.window_width_mm / 2.0
    for sign in (-1.0, 1.0):
        y_in = sign * (spec.half_length_mm - spec.window_depth_mm)
        y_out = sign * (spec.half_length_mm + CUT_MARGIN_MM)
        tools.append(
            _box(
                -half_window,
                half_window,
                min(y_in, y_out),
                max(y_in, y_out),
                -CUT_MARGIN_MM,
                thickness + CUT_MARGIN_MM,
            )
        )

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
    material and fuses to it; the blade stands in the end window with clearance all
    round, so its tip finishes flush with the plate's top face and is still free to
    flex the ledge under the board's sheet. The mouth therefore stays open through
    the plate, exactly as it does on a plate that takes an inserted retainer.
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


def build_clip(
    spec: Spec, centre_y_mm: float, slits: list[tuple[float, float]] | None = None
) -> cq.Workplane:
    """One integral C-loop at `centre_y_mm`.

    The blade - the arm carrying the ledge - points outboard, so the pair grips the
    same rib from either end, and the mouth faces the board.

    `slits` reproduces Warwick's finger relief across the clip's width. It is only
    used for the reference mesh: the printed plate stays one solid section.
    """
    outer, mouth = _loop_section(spec.section)
    mirror = centre_y_mm > 0.0
    body = _extrude_loop(outer, spec.section.width_along_slot_mm, mirror)
    void = _extrude_loop(
        mouth, spec.section.width_along_slot_mm + CUT_MARGIN_MM * 2.0, mirror
    )
    clip = body.cut(void)
    if slits:
        reach = spec.length_mm
        tools = [
            _box(
                x0,
                x1,
                -reach,
                reach,
                -spec.section.loop_drop_mm - CUT_MARGIN_MM,
                CUT_MARGIN_MM,
            )
            for x0, x1 in slits
        ]
        clip = _cut(clip, tools)
    return clip.translate((0.0, centre_y_mm, 0.0))


def build(spec: Spec) -> tuple[cq.Workplane, cq.Workplane]:
    base = build_base(spec)
    mount = base
    for sign in (-1.0, 1.0):
        mount = mount.union(build_clip(spec, sign * spec.clip_centre_y_mm))
    return mount.clean(), base.clean()


def build_reference_clip(spec: Spec) -> cq.Workplane:
    """Warwick's finger-relieved clip as a reference part: one section, three fingers.

    This is not the printed clip. It exists so the OEM's split section is on record
    next to the drawing that shows it.
    """
    return build_clip(spec, 0.0, spec.oem_slits).clean()


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


def _pieces(solid: cq.Solid, x0, x1, y0, y1, z0, z1) -> list:
    cut = solid.intersect(_box(x0, x1, y0, y1, z0, z1))
    return sorted((s.BoundingBox() for s in cut.Solids()), key=lambda b: b.xmin)


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

    def clip_span(z0, z1, outboard=True):
        """Overall x and y span of one clip over a z slab, both walls merged."""
        if outboard:
            span = (spec.clip_centre_y_mm - sec.half_outer_mm - PROBE_REACH_MM, y1)
        else:
            span = (y0, -(spec.clip_centre_y_mm - sec.half_outer_mm - PROBE_REACH_MM))
        pieces = _pieces(solid, x0, x1, span[0], span[1], z0, z1)
        if not pieces:
            return None
        return (
            min(p.xmin for p in pieces),
            max(p.xmax for p in pieces),
            min(p.ymin for p in pieces),
            max(p.ymax for p in pieces),
        )

    mid = _pieces(
        plate,
        x0,
        x1,
        -PROBE_STEP_MM,
        PROBE_STEP_MM,
        mid_z - PROBE_STEP_MM,
        mid_z + PROBE_STEP_MM,
    )[0]
    window = spec.half_length_mm - spec.window_depth_mm
    end = _pieces(
        plate,
        x0,
        x1,
        window + PROBE_STEP_MM,
        spec.half_length_mm - PROBE_STEP_MM,
        mid_z - PROBE_STEP_MM,
        mid_z + PROBE_STEP_MM,
    )
    window_gap = end[-1].xmin - end[0].xmax if len(end) == 2 else float("nan")

    band = (sec.probe_band_z_mm - PROBE_STEP_MM, sec.probe_band_z_mm)
    inset = (sec.ledge_z_mm + PROBE_STEP_MM, sec.ledge_z_mm + 2.0 * PROBE_STEP_MM)
    top_low = clip_span(*band)
    bottom_low = clip_span(*band, outboard=False)
    top_high = clip_span(*inset)
    top_centre = (top_low[2] + top_low[3]) / 2.0
    bottom_centre = (bottom_low[2] + bottom_low[3]) / 2.0

    exact(
        "overall width over the lobes",
        box.xlen,
        spec.width_mm,
        "72.0 on both B1 sheets",
    )
    exact("overall length", box.ylen, spec.length_mm, "125.5 on the alt side view")
    exact(
        "plate thickness",
        plate.BoundingBox().zlen,
        spec.plate_thickness_mm,
        "3 printed on section B-B",
    )
    exact(
        "side width",
        mid.xlen,
        spec.side_width_mm,
        "67 between the straight sides on both sheets",
    )
    exact(
        "lobe protrusion",
        (box.xlen - mid.xlen) / 2.0,
        (spec.width_mm - spec.side_width_mm) / 2.0,
        "the corner lobes standing proud of the straight sides",
    )
    exact(
        "end window width",
        window_gap,
        spec.window_width_mm,
        "24.6 wide, the same opening the A/E plates cut for an inserted retainer",
    )
    strip = _pieces(
        plate,
        -PROBE_HALF_MM,
        PROBE_HALF_MM,
        window - PROBE_REACH_MM,
        spec.half_length_mm + PROBE_REACH_MM,
        mid_z - PROBE_STEP_MM,
        mid_z + PROBE_STEP_MM,
    )[0]
    exact(
        "end window depth",
        spec.half_length_mm - strip.ymax,
        spec.window_depth_mm,
        "the mouth carried out to the end edge",
    )
    mouth_wall_mm = spec.half_length_mm - spec.window_depth_mm
    flag(
        "window lands on the mouth",
        f"{mouth_wall_mm:.2f} mm",
        f"{spec.clip_centre_y_mm - sec.half_mouth_mm:.2f} mm",
        abs(mouth_wall_mm - (spec.clip_centre_y_mm - sec.half_mouth_mm)) <= 0.3,
        "the window's inboard wall is the clip's mouth wall, so the plate cannot close the loop",
    )
    cavity = _pieces(
        solid,
        -PROBE_HALF_MM,
        PROBE_HALF_MM,
        spec.clip_centre_y_mm,
        spec.clip_centre_y_mm + sec.half_mouth_mm,
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
    blade_y = (
        spec.clip_centre_y_mm + sec.half_mouth_mm + PROBE_STEP_MM,
        spec.clip_centre_y_mm + sec.half_outer_mm - PROBE_STEP_MM,
    )
    blade = _pieces(
        solid,
        -PROBE_HALF_MM * 2.0,
        PROBE_HALF_MM * 2.0,
        blade_y[0],
        blade_y[1],
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
        -spec.window_width_mm / 2.0,
        spec.window_width_mm / 2.0,
        blade_y[0],
        blade_y[1],
        spec.plate_thickness_mm - PROBE_STEP_MM,
        spec.plate_thickness_mm - PROBE_STEP_MM * 0.5,
    )
    exact(
        "blade width in the window",
        (around[0].xmax - around[0].xmin) if len(around) == 1 else float("nan"),
        sec.width_along_slot_mm,
        "22 across a 24.6 window, so 1.30 clear a side",
    )
    exact(
        "clip width along x",
        top_low[1] - top_low[0],
        spec.section.width_along_slot_mm,
        "22, printed on the A/E sheets",
    )
    exact(
        "clip pair spacing",
        top_centre - bottom_centre,
        spec.clip_spacing_mm,
        "95.0, scaled off the alt side view",
    )
    exact(
        "clip drop below the plate",
        -box.zmin,
        spec.section.loop_drop_mm,
        "the retainer's 15.89 below the underside",
    )
    exact(
        "clip outer width",
        top_low[3] - top_low[2],
        spec.section.outer_width_mm,
        "19.0 in the retainer section",
    )
    exact(
        "ledge protrusion",
        top_low[3] - top_high[3],
        spec.section.ledge_protrusion_mm,
        "1.10 outboard, under the sheet: the blade is inset above the ledge so the sheet edge can pass",
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
        "2",
        len(ledges) == 2,
        "one upward face per clip, the one that catches the sheet",
    )
    if len(ledges) == 2:
        exact(
            "ledge drop",
            abs(ledges[0].Center().z),
            spec.section.ledge_drop_mm,
            "4.00 below the plate underside",
        )

    mouth = _pieces(
        solid,
        x0,
        x1,
        spec.clip_centre_y_mm - sec.half_outer_mm - PROBE_REACH_MM,
        y1,
        sec.probe_mouth_z_mm - PROBE_STEP_MM,
        sec.probe_mouth_z_mm,
    )
    exact(
        "clip mouth",
        mouth[-1].ymin - mouth[0].ymax if len(mouth) == 2 else float("nan"),
        spec.section.mouth_width_mm,
        "13.0, the retainer's mouth, measured above the arch springing",
    )
    walls = _pieces(
        solid,
        x0,
        x1,
        spec.clip_centre_y_mm - sec.half_outer_mm - PROBE_REACH_MM,
        y1,
        sec.probe_wall_z_mm - PROBE_STEP_MM,
        sec.probe_wall_z_mm,
    )
    if len(walls) == 2:
        exact(
            "clip post wall",
            walls[0].ylen,
            spec.section.post_wall_mm,
            "3.00, the rigid side of the loop",
        )
        exact(
            "clip blade wall",
            walls[1].ylen,
            spec.section.blade_wall_mm,
            "1.90, the side that has to flex",
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
                f"{pattern.id} recesses",
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
                if abs(abs(f.Center().y) - abs(pattern.y_mm)) < 0.5
            ]
            worst = max((abs(z - want) for z in zs), default=float("nan"))
            flag(
                f"{pattern.id} face side",
                f"{sum(zs) / len(zs):.2f} mm" if zs else "-",
                f"{want:.2f} mm",
                worst <= LEN_TOL_MM,
                f"recess centre has to sit on the {pattern.face_side} side",
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


def validate_clip(spec: Spec, clip: cq.Workplane, oem: bool) -> list[Check]:
    """Checks for a clip on its own, so the reference mesh is gated like the plate."""
    solid = clip.val()
    sec = spec.section
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

    exact(
        "width along x",
        box.xlen,
        sec.width_along_slot_mm,
        "22, printed on the A/E sheets",
    )
    exact("outer width", box.ylen, sec.outer_width_mm, "19.0 in the retainer section")
    exact("drop below the plate", -box.zmin, sec.loop_drop_mm)
    exact(
        "tip",
        box.zmax,
        sec.tip_z_mm,
        "flush with the plate's top face, the lip reaching through the slot",
    )

    z0 = -sec.loop_drop_mm + 2.0 * PROBE_STEP_MM
    fingers = _pieces(
        solid,
        box.xmin - PROBE_REACH_MM,
        box.xmax + PROBE_REACH_MM,
        box.ymin - PROBE_REACH_MM,
        box.ymax + PROBE_REACH_MM,
        z0,
        z0 + PROBE_STEP_MM,
    )
    want = spec.oem_fingers_mm if oem else [sec.width_along_slot_mm]
    flag(
        "fingers",
        str(len(fingers)),
        str(len(want)),
        len(fingers) == len(want),
        "the OEM's three fingers with two slits"
        if oem
        else "one solid section, as printed",
    )
    widths = [p.xmax - p.xmin for p in fingers]
    if len(widths) == len(want):
        worst = max(abs(w - v) for w, v in zip(widths, want))
        flag(
            "finger widths",
            " / ".join(f"{w:.2f}" for w in widths),
            " / ".join(f"{w:.2f}" for w in want),
            worst <= LEN_TOL_MM,
        )
    flag(
        "solid count",
        str(len(solid.Solids())),
        "1",
        len(solid.Solids()) == 1,
        "the fingers are joined by the arch",
    )
    return checks


def clip_report(spec: Spec, checks: list[Check], out: Path, oem: bool) -> str:
    sec = spec.section
    slit = spec.oem_slits[0][1] - spec.oem_slits[0][0] if spec.oem_slits else 0.0
    fingers = (
        " / ".join(f"{w:g}" for w in spec.oem_fingers_mm) + f" with {slit:g} slits"
        if oem
        else "one solid section, as printed"
    )
    lines = [
        f"125B clip{' (OEM relief, reference only)' if oem else ''}  ({Path(out).name})",
        "",
        "the shared retainer section, read in from commons/cfg/retainer.json",
        f"  width along x         {sec.width_along_slot_mm:7.2f} mm   22, printed on the A/E sheets",
        f"  outer width           {sec.outer_width_mm:7.2f} mm",
        f"  mouth                 {sec.mouth_width_mm:7.2f} mm",
        f"  drop below the plate  {sec.loop_drop_mm:7.2f} mm",
        f"  ledge                 {sec.ledge_protrusion_mm:.2f} mm out at {sec.ledge_drop_mm:.2f} below the underside",
        f"  tip                   {sec.tip_z_mm:7.2f} mm, flush with the plate's top face",
        f"  fingers               {fingers}",
        "",
        "checks",
    ]
    width = max(len(c.name) for c in checks)
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        lines.append(
            f"  {mark} {c.name:<{width}}  {c.value:>22}  {c.limit:>22}  {c.note}"
        )
    failed = [c for c in checks if not c.ok]
    lines.append("")
    lines.append(
        f"{len(checks) - len(failed)}/{len(checks)} checks pass"
        if not failed
        else f"{len(failed)} CHECK(S) FAILED"
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #


def report(spec: Spec, checks: list[Check], out: Path) -> str:
    sec = spec.section
    lines = [
        f"125B QuickMount, Type B1  ({Path(out).name})",
        "",
        "plate, from the two Type B1 sheets",
        f"  length                {spec.length_mm:7.2f} mm   125.5, alt side view",
        f"  width over the lobes  {spec.width_mm:7.2f} mm   72, both sheets",
        f"  width between sides   {spec.side_width_mm:7.2f} mm   67, both sheets",
        f"  thickness             {spec.plate_thickness_mm:7.2f} mm   3, section B-B",
        (
            f"  corner lobes          r {spec.lobe_radius_mm:.2f} about "
            f"({spec.lobe_x_mm:+.2f}, {spec.lobe_y_mm:+.2f}), "
            f"{(spec.width_mm - spec.side_width_mm) / 2.0:.1f} proud of each side"
        ),
        f"  end window            {spec.window_width_mm:7.2f} x {spec.window_depth_mm:.2f} mm, open to the end edge",
        "",
        "screws",
    ]
    for pattern in spec.patterns:
        face = (
            f", Ø{pattern.face_mm:g} recess {pattern.face_depth_mm:g} deep on the "
            f"{pattern.face_side} side"
            if pattern.face_mm
            else ""
        )
        lines.append(
            f"  {pattern.id:<10} {pattern.count:2d} x Ø{pattern.bore_mm:g} at ({pattern.x_mm:.2f}, {pattern.y_mm:.2f}){face}"
        )
    lines += [
        "",
        "clips, the shared retainer section with integral arms",
        f"  width along x         {sec.width_along_slot_mm:7.2f} mm   22, printed on the A/E sheets",
        f"  outer width           {sec.outer_width_mm:7.2f} mm",
        f"  mouth                 {sec.mouth_width_mm:7.2f} mm",
        f"  drop below the plate  {sec.loop_drop_mm:7.2f} mm   total {sec.drop_below_plate_top_mm:.2f} from the plate top",
        f"  tip                   flush with the plate's {spec.plate_thickness_mm:.2f} top face, through the window",
        f"  ledge                 {sec.ledge_protrusion_mm:.2f} mm out at {sec.ledge_drop_mm:.2f} below the underside",
        f"  centres               ±{spec.clip_centre_y_mm:.2f} mm, {spec.clip_spacing_mm:.2f} apart",
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

    verification = spec.raw.get("verification", {})
    if verification.get("cross_checks"):
        lines += ["", "verified against the drawing set"]
        for item in verification["cross_checks"]:
            lines.append(f"  {item['value']:<34} {item['verdict']}")
    return "\n".join(lines)


def summary(spec: Spec, checks: list[Check], out: Path) -> dict:
    return {
        "id": spec.raw["id"],
        "stl": str(out),
        "plate_mm": {
            "length": spec.length_mm,
            "width_over_lobes": spec.width_mm,
            "side_width": spec.side_width_mm,
            "thickness": spec.plate_thickness_mm,
            "end_window": [spec.window_width_mm, spec.window_depth_mm],
        },
        "screw_patterns": {
            p.id: {
                "count": p.count,
                "bore": p.bore_mm,
                "x": p.x_mm,
                "y": p.y_mm,
                "spot_face": p.face_mm,
            }
            for p in spec.patterns
        },
        "clips": {
            "count": 2,
            "centre_y": spec.clip_centre_y_mm,
            "spacing": spec.clip_spacing_mm,
            "pitch_multiple": spec.clip_pitch_multiple,
            "width": spec.section.width_along_slot_mm,
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
        choices=("all", "mount", "base", "clip"),
        default="all",
        help="mount is the plate with its clips, base the bare plate, clip one clip on its own",
    )
    ap.add_argument(
        "--clip-variant",
        choices=("solid", "oem"),
        default="solid",
        help="solid is what prints; oem cuts Warwick's finger relief and belongs in ref/",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="STL to write, instead of the default name",
    )
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    ap.add_argument(
        "--tolerance", type=float, default=0.01, help="STL linear tolerance"
    )
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    spec = load(args.config)
    mount, base = build(spec)
    checks = validate(spec, mount, base)

    jobs: list[tuple[str, cq.Workplane, Path, list[Check]]] = []
    if args.part in ("all", "mount"):
        jobs.append(("mount", mount, args.out or DEFAULT_STL, checks))
    if args.part in ("all", "base"):
        base_checks = [
            c
            for c in checks
            if c.name
            in {"plate thickness", "side width", "end window width", "end window depth"}
        ]
        base_checks.append(
            Check(
                "resting face flat",
                f"{base.val().BoundingBox().zmax:.2f} mm",
                f"{spec.plate_thickness_mm:.2f} mm",
                abs(base.val().BoundingBox().zmax - spec.plate_thickness_mm)
                <= LEN_TOL_MM,
                "the bare plate has to hand the riser a flat face",
            )
        )
        out = args.out if args.part == "base" and args.out else DEFAULT_BASE_STL
        jobs.append(("base", base, out, base_checks))
    if args.part == "clip":
        oem = args.clip_variant == "oem"
        clip = build_reference_clip(spec) if oem else build_clip(spec, 0.0)
        out = args.out or (spec.oem_reference if oem else DEFAULT_CLIP_STL)
        jobs.append(("clip", clip, out, validate_clip(spec, clip, oem)))

    ok = all(c.ok for _, _, _, cs in jobs for c in cs)
    for name, part, out, part_checks in jobs:
        out.parent.mkdir(parents=True, exist_ok=True)
        cq.exporters.export(
            part, str(out), tolerance=args.tolerance, angularTolerance=0.1
        )
        cq.exporters.export(part, str(out.with_suffix(".step")))
        if args.json:
            print(json.dumps(summary(spec, part_checks, out), indent=2))
        elif name == "clip":
            print(clip_report(spec, part_checks, out, args.clip_variant == "oem"))
        else:
            print(report(spec, part_checks, out))
        if len(jobs) > 1:
            print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
