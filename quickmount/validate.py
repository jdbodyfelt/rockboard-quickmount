"""Analytic checks for a generated plate.

Independent of CAD: these re-derive the engagement from the board profile and the
plate options, so a bad parameter combination fails fast with a number attached.

Run: python -m quickmount.validate
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .plate import (
    BoardProfile,
    PedalProfile,
    PlateOptions,
    barb_tip_y,
    keeper_geometry,
    shelf_z,
)

PETG_MAX_STRAIN = 0.015  # 1.5 % for repeated snap cycles


@dataclass
class Check:
    name: str
    value: float
    limit: str
    ok: bool

    def line(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        return f"[{mark}] {self.name:<44} {self.value:>8.3f}   ({self.limit})"


def springback_strain(deflection: float, t_arm: float, length: float) -> float:
    """Peak strain in a cantilever deflected by `deflection` at its free end.

    eps = 1.5 * t * d / L^2.  A screening estimate for the C flexure; a curved
    beam distributes the moment, so the real strain is lower. Conservative.
    """
    return 1.5 * t_arm * deflection / (length**2)


def screw_xy(pedal: PedalProfile):
    hx = pedal.width / 2.0 - pedal.screw_inset
    hy = pedal.depth / 2.0 - pedal.screw_inset
    return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)][: pedal.screw_count]


def check_design(
    pedal: PedalProfile,
    board: BoardProfile,
    opt: PlateOptions,
    under_sheet_clearance: float = 15.0,
) -> list[Check]:
    plate_d = pedal.depth - 2 * opt.edge_margin
    plate_w = pedal.width - 2 * opt.edge_margin
    geoms = keeper_geometry(board, plate_d, opt)
    shelf = shelf_z(board, opt)
    tip = barb_tip_y(board, opt)
    squeeze = tip - board.half_slot
    g0 = geoms[0]

    checks: list[Check] = []

    checks.append(
        Check(
            "barb squeeze per side",
            squeeze,
            f"> 0 and <= 2.0 (tip {tip:.2f} vs slot {board.half_slot:.2f})",
            0 < squeeze <= 2.0,
        )
    )

    strain = springback_strain(squeeze, opt.t_arm, g0.flexure_length)
    checks.append(
        Check(
            "flexure strain at full squeeze",
            strain * 100.0,
            f"% <= {PETG_MAX_STRAIN * 100:.1f} (L {g0.flexure_length:.1f} mm, t {opt.t_arm} mm)",
            strain <= PETG_MAX_STRAIN,
        )
    )

    checks.append(Check("barb ledge under the sheet", squeeze, ">= 0.8", squeeze >= 0.8))

    checks.append(
        Check(
            "rising branch inside slot while posting",
            board.half_slot - opt.branch_outer,
            "> 0",
            board.half_slot - opt.branch_outer > 0,
        )
    )
    checks.append(
        Check(
            "neck inside slot",
            board.half_slot - opt.node_outer,
            "> 0",
            board.half_slot - opt.node_outer > 0,
        )
    )

    checks.append(
        Check(
            "release gap between neck and branch",
            g0.release_gap,
            f">= {opt.release_gap_min:.1f} (finger or tool access)",
            g0.release_gap >= opt.release_gap_min,
        )
    )

    gap = (-shelf) - board.sheet_t
    checks.append(
        Check(
            "shelf clearance below sheet",
            gap,
            ">= 0 (positive lock)",
            0 <= gap <= 0.5,
        )
    )

    depth = abs(g0.u_bottom_z) - board.sheet_t
    checks.append(
        Check(
            "keeper depth below sheet fits board void",
            depth,
            f"< {under_sheet_clearance:.1f}",
            depth < under_sheet_clearance,
        )
    )

    if len(geoms) > 1:
        span = geoms[-1].centre_y - geoms[0].centre_y
        n = span / board.pitch
        checks.append(
            Check(
                "keeper spacing is a whole number of pitches",
                abs(n - round(n)) * board.pitch,
                f"== 0 ({span:.1f} mm = {round(n)} x {board.pitch:.1f})",
                abs(n - round(n)) < 1e-6,
            )
        )
        clearance_between = (geoms[-1].centre_y - tip) - (geoms[0].centre_y + tip)
        checks.append(
            Check("keepers do not overlap each other", clearance_between, "> 0", clearance_between > 0)
        )

    csk_r = pedal.screw_head_od / 2.0 + opt.csk_extra
    clear = math.inf
    for x, y in screw_xy(pedal):
        dx = max(abs(x) - opt.keeper_len_x / 2.0, 0.0)
        dy = min(max(abs(y - g.centre_y) - tip, 0.0) for g in geoms)
        clear = min(clear, math.hypot(dx, dy))
    checks.append(
        Check("screw countersink clear of keepers", clear - csk_r, "> 0", clear - csk_r > 0)
    )

    csk_depth = csk_r - opt.hole_d / 2.0
    checks.append(
        Check(
            "plate remaining under countersink",
            opt.t_plate - csk_depth,
            ">= 0.6",
            opt.t_plate - csk_depth >= 0.6,
        )
    )

    checks.append(Check("flexure wall thickness", opt.t_arm, ">= 1.2", opt.t_arm >= 1.2))
    checks.append(
        Check("plate footprint", min(plate_w, plate_d), ">= 40", min(plate_w, plate_d) >= 40)
    )

    return checks


def report(
    pedal: PedalProfile,
    board: BoardProfile,
    opt: PlateOptions,
    under_sheet_clearance: float = 15.0,
) -> bool:
    checks = check_design(pedal, board, opt, under_sheet_clearance)
    print(
        f"\n{pedal.pedal_id}  "
        f"(slot {board.slot_w} / rib {board.rib_w} / pitch {board.pitch} / sheet {board.sheet_t})"
    )
    for c in checks:
        print("  " + c.line())
    return all(c.ok for c in checks)


if __name__ == "__main__":
    from .build import ROOT, load_board, load_pedal

    board, board_raw = load_board()
    clearance = board_raw.get("sheets", {}).get("under_sheet_clearance_mm", 15.0)
    if board_raw.get("status") != "measured":
        print(
            f"NOTE: board profile '{board_raw['id']}' is '{board_raw.get('status')}'; "
            "dimensions are provisional until measured."
        )

    ok = True
    for path in sorted((ROOT / "catalog" / "pedals").glob("*.yaml")):
        pedal, _ = load_pedal(path)
        ok &= report(pedal, board, PlateOptions(), clearance)
    raise SystemExit(0 if ok else 1)
