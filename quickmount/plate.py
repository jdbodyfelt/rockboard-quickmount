"""Plate geometry.

Coordinates are *use* coordinates: the part is modelled as fitted to the board.

  z = 0    board-facing face of the plate (rests on the powder coat)
  z = t    pedal-facing face of the plate (screws pass through to the pedal)
  z < 0    hooks, hanging down through the slot grid

The plate is exported in print orientation (rotated 180 deg about X) so the
hooks point up; see docs/quickmount-mechanism.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import (
    Box,
    Cone,
    Cylinder,
    Plane,
    Polygon,
    Pos,
    RectangleRounded,
    Rot,
    chamfer,
    extrude,
    export_step,
    export_stl,
)


@dataclass(frozen=True)
class BoardProfile:
    slot_w: float
    rib_w: float
    pitch: float
    sheet_t: float

    @property
    def slot_centre_to_rib_mm(self) -> float:
        """Distance from a slot centreline to the start of the rib."""
        return self.slot_w / 2.0


@dataclass(frozen=True)
class PedalProfile:
    pedal_id: str
    width: float
    depth: float
    screw_inset: float
    screw_head_od: float
    screw_count: int = 4


@dataclass(frozen=True)
class PlateOptions:
    t_plate: float = 3.0
    edge_margin: float = 0.5
    corner_r: float = 3.0

    # hooks
    hook_count: int = 2
    stem_t: float = 3.0
    stem_len_x: float = 18.0
    barb_len: float = 6.5
    head_t: float = 2.2
    head_overlap: float = 0.6
    latch_clearance: float = 0.30
    slide_mm: float = 5.0

    # pedal screws
    hole_d: float = 3.8
    csk_extra: float = 0.2
    csk_angle_deg: float = 90.0

    # print
    bottom_chamfer: float = 0.4


@dataclass(frozen=True)
class PlateLayout:
    plate_w: float
    plate_d: float
    hook_y: tuple[float, ...]
    screw_xy: tuple[tuple[float, float], ...]
    head_z: tuple[float, float]
    stem_h: float

    def as_dict(self) -> dict:
        return {
            "plate_w_mm": round(self.plate_w, 3),
            "plate_d_mm": round(self.plate_d, 3),
            "hook_y_mm": [round(v, 3) for v in self.hook_y],
            "screw_xy_mm": [[round(x, 3), round(y, 3)] for x, y in self.screw_xy],
            "head_z_mm": [round(v, 3) for v in self.head_z],
            "stem_h_mm": round(self.stem_h, 3),
        }


def hook_positions(board: BoardProfile, depth: float, opt: PlateOptions) -> tuple[float, ...]:
    """Pick hook centre lines on a slot pitch, spread as widely as the plate allows."""
    usable = depth / 2.0 - opt.stem_len_x / 2.0 - 8.0
    if usable <= 0:
        raise ValueError(f"pedal depth {depth} mm too small for a {opt.stem_len_x} mm hook")
    n_pitch = math.floor(usable / board.pitch)
    if n_pitch < 1:
        n_pitch = 1
    half = n_pitch * board.pitch
    if opt.hook_count == 1:
        return (0.0,)
    return (-half, half)


def layout(pedal: PedalProfile, board: BoardProfile, opt: PlateOptions) -> PlateLayout:
    plate_w = pedal.width - 2 * opt.edge_margin
    plate_d = pedal.depth - 2 * opt.edge_margin
    hooks = hook_positions(board, plate_d, opt)

    latched = board.sheet_t + opt.latch_clearance + board.sheet_t * 0  # sheet + clearance
    head_bottom = -(latched + opt.head_t)
    stem_h = -head_bottom  # stem runs from plate face down to the head bottom

    inset = pedal.screw_inset
    hx = pedal.width / 2.0 - inset
    hy = pedal.depth / 2.0 - inset
    screws = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)][: pedal.screw_count]

    return PlateLayout(
        plate_w=plate_w,
        plate_d=plate_d,
        hook_y=hooks,
        screw_xy=tuple(screws),
        head_z=(head_bottom, -latched),
        stem_h=stem_h,
    )


def build_plate(pedal: PedalProfile, board: BoardProfile, opt: PlateOptions = PlateOptions()):
    lay = layout(pedal, board, opt)

    plate = extrude(RectangleRounded(lay.plate_w, lay.plate_d, opt.corner_r), amount=opt.t_plate)

    part = plate

    for y0 in lay.hook_y:
        stem = Pos(0, y0, -lay.stem_h / 2) * Box(opt.stem_len_x, opt.stem_t, lay.stem_h)
        part = part + stem

        # overlap the head into the stem so OCCT fuses a single solid
        y_in = y0 + opt.stem_t / 2 - opt.head_overlap
        y_out = y0 + opt.stem_t / 2 + opt.barb_len
        z_top = lay.head_z[1]
        z_bot = lay.head_z[0]
        pts = [
            (y_in, z_top),
            (y_out, z_top),
            (y_out - opt.head_t, z_bot),
            (y_in, z_bot),
        ]
        head = extrude(Plane.YZ * Polygon(*pts, align=None), amount=opt.stem_len_x)
        hb = head.bounding_box()
        head = Pos(-(hb.min.X + hb.max.X) / 2, 0, 0) * head
        part = part + head

    # pedal screws: countersunk from the board-facing face
    hole_r = opt.hole_d / 2
    csk_r = pedal.screw_head_od / 2 + opt.csk_extra
    csk_depth = csk_r - hole_r
    if csk_depth >= opt.t_plate - 0.6:
        raise ValueError(
            f"countersink {csk_depth:.2f} mm deep leaves under 0.6 mm of plate; "
            "increase plate thickness or reduce counterbore"
        )
    for x, y in lay.screw_xy:
        part = part - Pos(x, y, opt.t_plate / 2) * Cylinder(hole_r, opt.t_plate + 1)
        part = part - Pos(x, y, csk_depth / 2) * Cone(csk_r, hole_r, csk_depth)

    # deburr pedal face
    try:
        bottom_edges = part.edges().filter_by(lambda e: abs(e.center().Z) < 1e-6)
        if bottom_edges:
            part = chamfer(bottom_edges, opt.bottom_chamfer)
    except Exception:  # chamfer is cosmetic; never fail a build on it
        pass

    return part, lay


def to_print_orientation(part, opt: PlateOptions = PlateOptions()):
    """Hooks up, pedal face down on the bed."""
    return Pos(0, 0, opt.t_plate) * Rot(180, 0, 0) * part


def export(part, stl_path: str, step_path: str | None = None) -> None:
    export_stl(part, stl_path, tolerance=0.02, angular_tolerance=0.2)
    if step_path:
        export_step(part, step_path)
