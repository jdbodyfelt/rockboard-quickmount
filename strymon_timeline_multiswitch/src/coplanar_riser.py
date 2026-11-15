"""Generate separate TimeLine step and two-clip MultiSwitch QuickMount plate.

The TimeLine step reuses the J1 board interface and provides a full-width,
ribbed shelf. Its cable route is a circular front-to-rear tunnel; the cut is
applied after the shell and all ribs are joined. The separate MultiSwitch plate
uses the measured tray and four-screw pattern, with two horizontal C-loop clips.

    .venv/Scripts/python strymon_timeline_multiswitch/src/coplanar_riser.py
    .venv/Scripts/python strymon_timeline_multiswitch/src/coplanar_riser.py --check
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq


PROJECT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT / "cfg" / "strymon_timeline_multiswitch.json"
DWG = PROJECT / "dwg"
CUT = 1.0
TOL = 0.05


@dataclass(frozen=True)
class Check:
    name: str
    value: str
    limit: str
    ok: bool
    note: str


@dataclass(frozen=True)
class Spec:
    raw: dict
    config_path: Path
    j1_length: float
    j1_depth: float
    base_thickness: float
    top_skin: float
    wall: float
    rib: float
    ribs_y: tuple[float, ...]
    ribs_x: tuple[float, ...]
    screw_tube_wall: float
    timeline_bottom_z: float
    pocket_depth: float
    pocket_width: float
    pocket_depth_y: float
    shelf_margin: float
    edge_radius: float
    timeline_dx: float
    timeline_dy: float
    timeline_bore: float
    timeline_counterbore: float
    timeline_counterbore_depth: float
    cable_stadium_width: float
    cable_stadium_length: float
    cable_x_from_left: tuple[float, ...]
    cable_z: float
    bottom_stadium_width: float
    bottom_stadium_length: float
    bottom_stadium_angles: tuple[float, ...]
    multi_width: float
    multi_depth: float
    multi_radius: float
    multi_dx: float
    multi_dy: float
    multi_bore: float
    multi_counterbore: float
    multi_counterbore_depth: float
    clip_centres_x: tuple[float, ...]
    clip_centre_y: float
    clip_slot_width: float
    clip_slot_depth: float
    step_stl: Path
    step_step: Path
    multi_stl: Path
    multi_step: Path

    @property
    def step_top_bottom_z(self) -> float:
        return self.step_top_z - self.top_skin

    @property
    def step_top_z(self) -> float:
        return self.timeline_bottom_z + self.pocket_depth

    @property
    def pocket_floor_z(self) -> float:
        return self.timeline_bottom_z

    @property
    def shelf_width(self) -> float:
        return self.j1_length + 2 * self.shelf_margin

    @property
    def shelf_depth(self) -> float:
        return self.j1_depth + 2 * self.shelf_margin

    @property
    def cable_x(self) -> tuple[float, ...]:
        return tuple(-self.j1_length / 2 + value for value in self.cable_x_from_left)

    @property
    def screw_access_diameter(self) -> float:
        return self.timeline_bore + 0.2


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_j1():
    source = PROJECT / "src" / "quickmount_j1.py"
    module_spec = importlib.util.spec_from_file_location("quickmount_j1_for_separate_mounts", source)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"cannot load J1 generator: {source}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def load(path: Path = CONFIG) -> Spec:
    raw = _read(path)
    plate = raw["quickmount"]["plate"]
    design = raw["separate_mounts"]
    step = design["timeline_step"]
    multi = design["multiswitch_plate"]
    structure = design["structure"]
    timeline_pattern = step["j1_clearance_pattern_mm"]
    multi_pattern = multi["screw_pattern_mm"]
    clips = multi["clips"]
    base = float(structure["base_thickness_mm"])
    top_skin = float(structure["top_skin_mm"])
    pocket = step.get("pocket")
    if pocket:
        timeline_bottom_z = float(step["timeline_bottom_z_mm"])
        pocket_depth = float(pocket["sink_depth_mm"])
        pocket_width = float(pocket["width_mm"])
        pocket_depth_y = float(pocket["outline_depth_mm"])
        shelf_margin = float(pocket["outer_shelf_margin_mm"])
        edge_radius = float(pocket["edge_radius_mm"])
    else:
        timeline_bottom_z = float(step["support_top_z_mm"])
        pocket_depth = 0.0
        pocket_width = float(plate["length_mm"])
        pocket_depth_y = float(plate["width_mm"])
        shelf_margin = 0.0
        edge_radius = float(step["edge_radius_mm"])
    step_top = timeline_bottom_z + pocket_depth
    if step_top <= base + top_skin:
        raise ValueError("TimeLine shelf must sit above the J1 base plate")
    return Spec(
        raw=raw,
        config_path=path,
        j1_length=float(plate["length_mm"]),
        j1_depth=float(plate["width_mm"]),
        base_thickness=base,
        top_skin=top_skin,
        wall=float(structure["wall_thickness_mm"]),
        rib=float(structure["rib_thickness_mm"]),
        ribs_y=tuple(float(value) for value in structure["ribs_y_mm"]),
        ribs_x=tuple(float(value) for value in structure["ribs_x_mm"]),
        screw_tube_wall=float(structure["screw_tube_wall_mm"]),
        timeline_bottom_z=timeline_bottom_z,
        pocket_depth=pocket_depth,
        pocket_width=pocket_width,
        pocket_depth_y=pocket_depth_y,
        shelf_margin=shelf_margin,
        edge_radius=edge_radius,
        timeline_dx=float(timeline_pattern["dx"]),
        timeline_dy=float(timeline_pattern["dy"]),
        timeline_bore=float(timeline_pattern["bore"]),
        timeline_counterbore=float(timeline_pattern["counterbore"]),
        timeline_counterbore_depth=float(timeline_pattern["counterbore_depth"]),
        cable_stadium_width=float(step["cable_tunnel"]["stadium_width_mm"]),
        cable_stadium_length=float(step["cable_tunnel"]["stadium_length_mm"]),
        cable_x_from_left=tuple(float(value) for value in step["cable_tunnel"]["centres_x_from_left_mm"]),
        cable_z=float(step["cable_tunnel"]["centre_z_mm"]),
        bottom_stadium_width=float(step["cable_tunnel"]["bottom_x_pass_through"]["width_mm"]),
        bottom_stadium_length=float(step["cable_tunnel"]["bottom_x_pass_through"]["length_mm"]),
        bottom_stadium_angles=tuple(float(value) for value in step["cable_tunnel"]["bottom_x_pass_through"]["angles_deg"]),
        multi_width=float(multi["tray_mm"]["width"]),
        multi_depth=float(multi["tray_mm"]["depth"]),
        multi_radius=float(multi["tray_mm"]["corner_radius"]),
        multi_dx=float(multi_pattern["dx"]),
        multi_dy=float(multi_pattern["dy"]),
        multi_bore=float(multi_pattern["clearance_bore"]),
        multi_counterbore=float(multi_pattern["counterbore_dia"]),
        multi_counterbore_depth=float(multi_pattern["counterbore_depth"]),
        clip_centres_x=tuple(float(value) for value in clips["centres_x_mm"]),
        clip_centre_y=float(clips["centre_y_mm"]),
        clip_slot_width=float(clips["slot_width_mm"]),
        clip_slot_depth=float(clips["slot_depth_mm"]),
        step_stl=(PROJECT / design["timeline_step"]["drawing"]).resolve(),
        step_step=(PROJECT / design["timeline_step"]["step"]).resolve(),
        multi_stl=(PROJECT / design["multiswitch_plate"]["drawing"]).resolve(),
        multi_step=(PROJECT / design["multiswitch_plate"]["step"]).resolve(),
    )


def _box(x: float, y: float, z: float, cx: float, cy: float, z0: float) -> cq.Workplane:
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, False)).translate((cx, cy, z0))


def _cylinder_z(diameter: float, z0: float, height: float, x: float, y: float) -> cq.Solid:
    return cq.Solid.makeCylinder(diameter / 2, height, cq.Vector(x, y, z0))


def _stadium_y_tools(width: float, length: float, x: float, z: float, y_span: float) -> list[cq.Solid]:
    """A vertical stadium profile, extruded front-to-rear along Y."""
    straight = max(0.0, length - width)
    tools = [_box(width, y_span, straight, x, 0.0, z - straight / 2).val()]
    y0 = -y_span / 2
    for end_z in (z - straight / 2, z + straight / 2):
        tools.append(cq.Solid.makeCylinder(width / 2, y_span, cq.Vector(x, y0, end_z), cq.Vector(0, 1, 0)))
    return tools


def _stadium_xy_tools(width: float, length: float, angle_deg: float, z0: float, height: float) -> list[cq.Solid]:
    """A horizontal stadium cut through the base plate, rotated in the XY plane."""
    straight = max(0.0, length - width)
    bar = _box(straight, width, height, 0.0, 0.0, z0).rotate((0, 0, 0), (0, 0, 1), angle_deg).val()
    angle = math.radians(angle_deg)
    dx = straight / 2 * math.cos(angle)
    dy = straight / 2 * math.sin(angle)
    return [bar, _cylinder_z(width, z0, height, dx, dy), _cylinder_z(width, z0, height, -dx, -dy)]


def _cut(part: cq.Workplane, tools: list[cq.Solid]) -> cq.Workplane:
    if not tools:
        return part
    stack = cq.Workplane("XY")
    for tool in tools:
        stack = stack.add(tool)
    return part.cut(stack)


def _timeline_positions(spec: Spec) -> list[tuple[float, float]]:
    return [(x, y) for x in (-spec.timeline_dx / 2, spec.timeline_dx / 2) for y in (-spec.timeline_dy / 2, spec.timeline_dy / 2)]


def _multi_positions(spec: Spec) -> list[tuple[float, float]]:
    return [(x, y) for x in (-spec.multi_dx / 2, spec.multi_dx / 2) for y in (-spec.multi_dy / 2, spec.multi_dy / 2)]


def build_timeline_step(spec: Spec) -> cq.Workplane:
    j1 = _load_j1()
    j1_spec = j1.load(spec.config_path)
    board_mount, _ = j1.build(j1_spec)
    timeline_positions = _timeline_positions(spec)

    # The J1 offers three generic patterns. Only its 142 x 108 clearance pattern
    # aligns with the measured TimeLine screws; restore the other two patterns to
    # solid plate material so they do not appear as unexplained pockets.
    for pattern in j1_spec.patterns:
        if pattern.id == "clearance":
            continue
        fill_diameter = max(pattern.bore_mm, pattern.face_mm or 0.0)
        for x, y in pattern.positions:
            board_mount = board_mount.union(_cylinder_z(fill_diameter, 0.0, spec.base_thickness, x, y))

    base_tools: list[cq.Solid] = []
    for x, y in timeline_positions:
        base_tools.append(_cylinder_z(spec.screw_access_diameter, -CUT, spec.base_thickness + 2 * CUT, x, y))
    for angle in spec.bottom_stadium_angles:
        base_tools.extend(_stadium_xy_tools(spec.bottom_stadium_width, spec.bottom_stadium_length, angle, -CUT, spec.base_thickness + 2 * CUT))
    board_mount = _cut(board_mount.clean(), base_tools)

    wall_height = spec.step_top_bottom_z - spec.base_thickness
    shelf = _box(spec.shelf_width, spec.shelf_depth, spec.top_skin, 0.0, 0.0, spec.step_top_bottom_z)
    shelf = shelf.edges("|Z").fillet(spec.edge_radius).edges(">Z").fillet(spec.edge_radius)
    shell = shelf
    shell = shell.union(_box(spec.wall, spec.j1_depth, wall_height, -spec.j1_length / 2 + spec.wall / 2, 0.0, spec.base_thickness))
    shell = shell.union(_box(spec.wall, spec.j1_depth, wall_height, spec.j1_length / 2 - spec.wall / 2, 0.0, spec.base_thickness))
    shell = shell.union(_box(spec.j1_length - 2 * spec.wall, spec.wall, wall_height, 0.0, -spec.j1_depth / 2 + spec.wall / 2, spec.base_thickness))
    shell = shell.union(_box(spec.j1_length - 2 * spec.wall, spec.wall, wall_height, 0.0, spec.j1_depth / 2 - spec.wall / 2, spec.base_thickness))
    for y in spec.ribs_y:
        shell = shell.union(_box(spec.j1_length - 2 * spec.wall, spec.rib, wall_height, 0.0, y, spec.base_thickness))
    for x in spec.ribs_x:
        shell = shell.union(_box(spec.rib, spec.j1_depth - 2 * spec.wall, wall_height, x, 0.0, spec.base_thickness))
    for x, y in timeline_positions:
        shell = shell.union(_cylinder_z(spec.screw_access_diameter + 2 * spec.screw_tube_wall, spec.base_thickness, wall_height, x, y))
    shell = shell.clean().edges("|Z").fillet(min(1.0, spec.edge_radius))

    tools: list[cq.Solid] = []
    if spec.pocket_depth > 0:
        tools.append(_box(spec.pocket_width, spec.pocket_depth_y, spec.pocket_depth + CUT, 0.0, 0.0, spec.pocket_floor_z).val())
    for x, y in timeline_positions:
        tools.append(_cylinder_z(spec.screw_access_diameter, spec.base_thickness - CUT, spec.step_top_z - spec.base_thickness + 2 * CUT, x, y))
        tools.append(_cylinder_z(spec.timeline_counterbore, spec.step_top_bottom_z - CUT, spec.timeline_counterbore_depth + CUT, x, y))
    # Cut after all ribs and screw tubes are joined: every stadium remains clear.
    for x in spec.cable_x:
        tools.extend(_stadium_y_tools(spec.cable_stadium_width, spec.cable_stadium_length, x, spec.cable_z, spec.j1_depth + 2 * CUT))
    shell = _cut(shell.clean(), tools)
    return board_mount.union(shell).clean()


def build_multiswitch_plate(spec: Spec) -> cq.Workplane:
    j1 = _load_j1()
    j1_spec = j1.load(spec.config_path)
    plate = _box(spec.multi_width, spec.multi_depth, spec.base_thickness, 0.0, 0.0, 0.0)
    plate = plate.edges("|Z").fillet(1.0).edges(">Z").fillet(1.0)
    if spec.multi_radius > 0:
        plate = plate.edges("|Z").fillet(spec.multi_radius)
    tools: list[cq.Solid] = []
    for x, y in _multi_positions(spec):
        tools.append(_cylinder_z(spec.multi_bore, -CUT, spec.base_thickness + 2 * CUT, x, y))
        tools.append(_cylinder_z(spec.multi_counterbore, -CUT, spec.multi_counterbore_depth + CUT, x, y))
    slot_centre_y = -spec.multi_depth / 2 + spec.clip_slot_depth / 2
    for x in spec.clip_centres_x:
        tools.append(_box(spec.clip_slot_width, spec.clip_slot_depth, spec.base_thickness + 2 * CUT, x, slot_centre_y, -CUT).val())
    plate = _cut(plate, tools)
    for x in spec.clip_centres_x:
        plate = plate.union(j1.build_clip(j1_spec, x, spec.clip_centre_y))
    return plate.clean()


def validate(spec: Spec, step: cq.Workplane, multi: cq.Workplane) -> list[Check]:
    step_box = step.val().BoundingBox()
    multi_box = multi.val().BoundingBox()
    pocket_faces = [
        face
        for face in step.val().Faces()
        if face.geomType() == "PLANE"
        and face.normalAt().z > 0.99
        and abs(face.Center().z - spec.pocket_floor_z) <= TOL
    ]
    return [
        Check("TimeLine support plane", f"{spec.timeline_bottom_z:.2f} mm", "42.60 mm", bool(pocket_faces) if spec.pocket_depth > 0 else abs(step_box.zmax - spec.step_top_z) <= TOL, "pocket floor" if spec.pocket_depth > 0 else "flat rounded shelf"),
        Check("outer shelf top", f"{step_box.zmax:.2f} mm", f"{spec.step_top_z:.2f} mm", abs(step_box.zmax - spec.step_top_z) <= TOL, "rounded external shelf"),
        Check("TimeLine J1 clearance", f"{spec.timeline_dx:.2f} x {spec.timeline_dy:.2f} mm", "142 x 108 mm", abs(spec.timeline_dx - 142) <= TOL and abs(spec.timeline_dy - 108) <= TOL, "matches the J1 clearance pattern"),
        Check("front/rear stadium tunnels", f"{len(spec.cable_x)} x {spec.cable_stadium_width:.2f} x {spec.cable_stadium_length:.2f} mm", "two vertically centred openings", len(spec.cable_x) == 2 and all(-spec.j1_length / 2 < x < spec.j1_length / 2 for x in spec.cable_x) and spec.base_thickness + spec.cable_stadium_length / 2 < spec.cable_z < spec.step_top_bottom_z - spec.cable_stadium_length / 2, "subtracted after ribs and tubes are fused"),
        Check("bottom X stadiums", f"{len(spec.bottom_stadium_angles)} x {spec.bottom_stadium_width:.2f} x {spec.bottom_stadium_length:.2f} mm", "two diagonal base pass-throughs", len(spec.bottom_stadium_angles) == 2 and set(spec.bottom_stadium_angles) == {-45.0, 45.0}, "central X avoids the corner clips and TimeLine screw tubes"),
        Check("TimeLine screw tubes", f"{len(_timeline_positions(spec))} x Ø{spec.screw_access_diameter:.2f} mm", "four access bores", len(_timeline_positions(spec)) == 4 and spec.screw_access_diameter > spec.timeline_bore, "0.2 mm clearance bores run from the J1 counterbores to the upper mount holes"),
        Check("MultiSwitch plate footprint", f"{multi_box.xlen:.2f} x {multi_box.ylen:.2f} mm", f"{spec.multi_width:.2f} x {spec.multi_depth:.2f} mm", abs(multi_box.xlen - spec.multi_width) <= TOL and abs(multi_box.ylen - spec.multi_depth) <= TOL, "two clips hang below and do not change the 2D footprint"),
        Check("horizontal MultiSwitch clips", str(len(spec.clip_centres_x)), "2", len(spec.clip_centres_x) == 2 and abs(spec.clip_centres_x[0] + spec.clip_centres_x[1]) <= TOL, "centres share one Y coordinate"),
        Check("TimeLine step solid count", str(len(step.val().Solids())), "1", len(step.val().Solids()) == 1, "J1 interface and shell are fused"),
        Check("MultiSwitch plate solid count", str(len(multi.val().Solids())), "1", len(multi.val().Solids()) == 1, "plate and both clips are fused"),
    ]


def export(part: cq.Workplane, stl: Path, step: Path, tolerance: float) -> None:
    stl.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(part, str(stl), tolerance=tolerance, angularTolerance=0.1)
    cq.exporters.export(part, str(step))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--part", choices=("all", "timeline", "multiswitch"), default="all")
    parser.add_argument("--check", action="store_true", help="validate without exporting")
    parser.add_argument("--tolerance", type=float, default=0.01, help="STL mesh deflection in mm")
    args = parser.parse_args(argv)
    spec = load(args.config)
    step = build_timeline_step(spec)
    multi = build_multiswitch_plate(spec)
    checks = validate(spec, step, multi)
    for check in checks:
        print(f"{'ok' if check.ok else 'FAIL':<4} {check.name}: {check.value} ({check.limit}) — {check.note}")
    if args.check:
        return 0 if all(check.ok for check in checks) else 1
    if args.part in ("all", "timeline"):
        export(step, spec.step_stl, spec.step_step, args.tolerance)
    if args.part in ("all", "multiswitch"):
        export(multi, spec.multi_stl, spec.multi_step, args.tolerance)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
