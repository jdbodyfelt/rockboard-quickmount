"""C-keeper geometry.

Coordinates are *use* coordinates: the part is modelled as fitted to the board.

  z = 0    board-facing face of the plate (rests on the powder coat)
  z = t    pedal-facing face of the plate (screws pass through from above)
  z < 0    keepers, hanging through a slot into the board's void

Each keeper is a pair of mirrored **C-shaped flexures**. A flexure is rooted at
the plate, posts down through the slot, curves through the void and rises back up
to a free end carrying an outward barb just under the sheet. Insertion snaps over
a 45 deg ramp; release is by pinching the two U-bends from under the board.

See docs/quickmount-mechanism.md for the mechanism, sizing and strain budget.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import (
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

from .profiles import stroke_polygon


@dataclass(frozen=True)
class BoardProfile:
    slot_w: float
    rib_w: float
    pitch: float
    sheet_t: float

    @property
    def half_slot(self) -> float:
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
    # plate
    t_plate: float = 3.0
    edge_margin: float = 0.5
    corner_r: float = 3.0

    # keeper arrangement
    keeper_count: int = 2          # keepers per plate (one per slot)
    keeper_len_x: float = 16.0     # extent along the slot's long axis

    # C flexure
    t_arm: float = 1.8             # flexure wall thickness
    node_outer: float = 5.0        # outer face of the neck, from keeper centre
    branch_outer: float = 9.9      # outer face of the rising branch
    u_depth: float = 9.3           # lowest point of the flexure, below plate face
    barb_overlap: float = 1.2      # barb reach beyond the slot edge
    barb_tip_flat: float = 0.20    # vertical land at the barb tip
    latch_clearance: float = 0.30  # shelf to sheet underside
    ramp_deg: float = 45.0
    release_gap_min: float = 3.0   # neck-to-branch opening for a pinch or tool

    # pedal screws
    hole_d: float = 3.8
    csk_extra: float = 0.2
    csk_angle_deg: float = 90.0

    # print
    bottom_chamfer: float = 0.4


@dataclass(frozen=True)
class KeeperGeom:
    """Resolved dimensions of one keeper, used by the validator."""

    centre_y: float
    shelf_z: float
    barb_tip_y: float
    branch_outer_y: float
    node_outer_y: float
    release_gap: float
    u_bottom_z: float
    flexure_length: float
    ramp_run: float


def shelf_z(board: BoardProfile, opt: PlateOptions) -> float:
    """z of the barb's upper (load-bearing) face: just below the sheet."""
    return -(board.sheet_t + opt.latch_clearance)


def barb_tip_y(board: BoardProfile, opt: PlateOptions) -> float:
    return board.half_slot + opt.barb_overlap


def keeper_centres(board: BoardProfile, plate_d: float, opt: PlateOptions) -> tuple[float, ...]:
    """Keeper centre lines, spaced on whole slot pitches."""
    reach = barb_tip_y(board, opt) + abs(shelf_z(board, opt))
    usable = plate_d / 2.0 - reach - 4.0
    if usable <= 0:
        raise ValueError(f"pedal depth {plate_d} mm too small for a keeper")
    n = max(1, math.floor(usable / board.pitch))
    if opt.keeper_count == 1:
        return (0.0,)
    half = n * board.pitch
    return (-half, half)


def flexure_path(opt: PlateOptions) -> list[tuple[float, float]]:
    """Centreline of one C flexure, in (y, z), for the +Y side.

    Runs from inside the plate, down the neck, through the U-bend in the void and
    back up the rising branch to just under the barb.
    """
    h = opt.t_arm / 2.0
    nc = opt.node_outer - h      # neck centreline
    bc = opt.branch_outer - h    # rising-branch centreline
    zb = -opt.u_depth + h        # U-bend centreline depth

    return [
        (nc, 1.0),                    # inside the plate, hidden by the union
        (nc, -2.0),
        (nc, -4.6),
        (nc + 0.20, -6.6),
        (nc + 0.85, -8.2),
        ((nc + bc) / 2.0, zb),        # bottom of the U
        (bc - 0.85, -8.2),
        (bc - 0.20, -6.6),
        (bc, -4.6),
        (bc, -3.6),                   # square cap lands near -2.7, under the barb
    ]


def barb_polygon(board: BoardProfile, opt: PlateOptions) -> list[tuple[float, float]]:
    """+Y barb wedge: flat shelf on top, 45 deg ramp underneath."""
    shelf = shelf_z(board, opt)
    tip = barb_tip_y(board, opt)
    outer = opt.branch_outer
    inner = outer - opt.t_arm
    run = tip - outer
    ramp_drop = run / math.tan(math.radians(opt.ramp_deg))
    return [
        (inner, shelf),
        (tip, shelf),
        (tip, shelf - opt.barb_tip_flat),
        (outer, shelf - opt.barb_tip_flat - ramp_drop),
        (inner, shelf - opt.barb_tip_flat - ramp_drop),
    ]


def _extrude_along_x(pts: list[tuple[float, float]], length: float):
    """Extrude a (y, z) polygon along +X, centred on x = 0."""
    face = Plane.YZ * Polygon(*pts, align=None)
    solid = extrude(face, amount=length)
    bb = solid.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, 0, 0) * solid


def keeper_geometry(board: BoardProfile, plate_d: float, opt: PlateOptions) -> tuple[KeeperGeom, ...]:
    shelf = shelf_z(board, opt)
    tip = barb_tip_y(board, opt)
    path = flexure_path(opt)
    developed = sum(math.dist(path[i], path[i + 1]) for i in range(len(path) - 1))
    developed += abs(path[-1][1] - shelf)

    return tuple(
        KeeperGeom(
            centre_y=c,
            shelf_z=shelf,
            barb_tip_y=tip,
            branch_outer_y=opt.branch_outer,
            node_outer_y=opt.node_outer,
            release_gap=(opt.branch_outer - opt.t_arm) - opt.node_outer,
            u_bottom_z=-opt.u_depth,
            flexure_length=developed,
            ramp_run=tip - opt.branch_outer,
        )
        for c in keeper_centres(board, plate_d, opt)
    )


def build_keeper(board: BoardProfile, opt: PlateOptions):
    """One keeper: two mirrored C flexures plus their barbs."""
    pts = list(stroke_polygon(flexure_path(opt), opt.t_arm).exterior.coords)[:-1]
    solid = _extrude_along_x(pts, opt.keeper_len_x)
    solid = solid + _extrude_along_x([(-y, z) for y, z in pts], opt.keeper_len_x)

    barb = barb_polygon(board, opt)
    solid = solid + _extrude_along_x(barb, opt.keeper_len_x)
    solid = solid + _extrude_along_x([(-y, z) for y, z in barb], opt.keeper_len_x)
    return solid


def build_plate(pedal: PedalProfile, board: BoardProfile, opt: PlateOptions = PlateOptions()):
    plate_w = pedal.width - 2 * opt.edge_margin
    plate_d = pedal.depth - 2 * opt.edge_margin
    geoms = keeper_geometry(board, plate_d, opt)

    layout = {
        "plate_w_mm": round(plate_w, 3),
        "plate_d_mm": round(plate_d, 3),
        "keeper_y_mm": [round(g.centre_y, 3) for g in geoms],
        "screw_xy_mm": [],
        "shelf_z_mm": round(shelf_z(board, opt), 3),
        "barb_tip_y_mm": round(barb_tip_y(board, opt), 3),
        "u_bottom_z_mm": -opt.u_depth,
        "flexure_length_mm": round(geoms[0].flexure_length, 2),
    }

    part = extrude(RectangleRounded(plate_w, plate_d, opt.corner_r), amount=opt.t_plate)

    keeper = build_keeper(board, opt)
    for g in geoms:
        part = part + Pos(0, g.centre_y, 0) * keeper

    inset = pedal.screw_inset
    hx = pedal.width / 2.0 - inset
    hy = pedal.depth / 2.0 - inset
    screws = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)][: pedal.screw_count]

    hole_r = opt.hole_d / 2.0
    csk_r = pedal.screw_head_od / 2.0 + opt.csk_extra
    csk_depth = csk_r - hole_r
    for x, y in screws:
        part = part - Pos(x, y, opt.t_plate / 2) * Cylinder(hole_r, opt.t_plate + 1)
        part = part - Pos(x, y, csk_depth / 2) * Cone(csk_r, hole_r, csk_depth)
        layout["screw_xy_mm"].append([round(x, 3), round(y, 3)])

    try:
        bottom_edges = part.edges().filter_by(lambda e: abs(e.center().Z) < 1e-6)
        if bottom_edges:
            part = chamfer(bottom_edges, opt.bottom_chamfer)
    except Exception:  # cosmetic only
        pass

    return part, layout


def to_print_orientation(part, opt: PlateOptions = PlateOptions()):
    """Keepers up, pedal face on the bed."""
    return Pos(0, 0, opt.t_plate) * Rot(180, 0, 0) * part


def export(part, stl_path: str, step_path: str | None = None) -> None:
    export_stl(part, stl_path, tolerance=0.02, angular_tolerance=0.2)
    if step_path:
        export_step(part, step_path)
