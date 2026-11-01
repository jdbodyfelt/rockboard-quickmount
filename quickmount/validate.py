"""Engagement checks for a generated plate.

These are analytic checks against the board profile, independent of CAD.
Run: python -m quickmount.validate
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .plate import BoardProfile, PedalProfile, PlateOptions, layout


@dataclass
class Check:
    name: str
    value: float
    limit: str
    ok: bool

    def line(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        return f"[{mark}] {self.name:<46} {self.value:>8.2f} mm   ({self.limit})"


def check_engagement(pedal: PedalProfile, board: BoardProfile, opt: PlateOptions) -> list[Check]:
    lay = layout(pedal, board, opt)
    half_slot = board.slot_w / 2.0
    checks: list[Check] = []

    stem_half = opt.stem_t / 2.0
    y_out = stem_half + opt.barb_len                      # barb tip, relative to hook centre
    head_top = board.sheet_t + opt.latch_clearance        # depth of locking face below plate face
    head_bottom = -(head_top + opt.head_t)

    # 1. insertion: the whole barb must pass through the slot opening
    checks.append(
        Check(
            "insertion: barb tip inside slot half-width",
            half_slot - y_out,
            f"> 0 (barb tip {y_out:.2f} vs {half_slot:.2f})",
            half_slot - y_out > 0,
        )
    )

    # 2. latched: the locking face must sit under the rib
    under = (y_out + opt.slide_mm) - half_slot
    checks.append(
        Check(
            "latched: barb engaged under rib",
            under,
            f">= 2.0 (slide {opt.slide_mm:.1f} mm)",
            under >= 2.0,
        )
    )

    # 3. latched: the stem must still be inside the slot
    checks.append(
        Check(
            "latched: stem still inside slot",
            half_slot - (stem_half + opt.slide_mm),
            "> 0",
            half_slot - (stem_half + opt.slide_mm) > 0,
        )
    )

    # 4. barb must not reach the far side of the rib
    checks.append(
        Check(
            "latched: barb clear of next slot",
            (half_slot + board.rib_w) - (y_out + opt.slide_mm),
            "> 0",
            (half_slot + board.rib_w) - (y_out + opt.slide_mm) > 0,
        )
    )

    # 5. hook depth must clear the sheet
    checks.append(
        Check(
            "hook head entirely below sheet",
            -(head_top - board.sheet_t),
            f"> 0 (gap {opt.latch_clearance:.2f})",
            head_top - board.sheet_t >= 0,
        )
    )

    # 6. the head must pass under while the stem occupies the slot
    checks.append(
        Check(
            "stem height covers head",
            -head_bottom - (lay.stem_h),
            "== 0",
            abs(-head_bottom - lay.stem_h) < 1e-9,
        )
    )

    # 7. hooks on a slot pitch so a phase exists that lands both in slots
    if len(lay.hook_y) > 1:
        span = lay.hook_y[-1] - lay.hook_y[0]
        n = span / board.pitch
        checks.append(
            Check(
                "hook spacing is a whole number of pitches",
                abs(n - round(n)) * board.pitch,
                f"== 0 ({span:.1f} mm = {round(n)} x {board.pitch:.1f})",
                abs(n - round(n)) < 1e-6,
            )
        )

    # 8. pedal screws must not collide with the hook stems
    clear = math.inf
    for x, y in lay.screw_xy:
        dx = max(abs(x) - opt.stem_len_x / 2.0, 0.0)
        dy = min(abs(abs(y) - abs(hy)) for hy in lay.hook_y)
        clear = min(clear, math.hypot(dx, dy))
    csk_r = pedal.screw_head_od / 2.0 + opt.csk_extra
    checks.append(
        Check(
            "screw countersink clear of hook stem",
            clear - csk_r,
            "> 0",
            clear - csk_r > 0,
        )
    )

    # 9. countersink leaves printable plate under the head
    csk_depth = csk_r - opt.hole_d / 2.0
    checks.append(
        Check(
            "plate remaining under countersink",
            opt.t_plate - csk_depth,
            ">= 0.6",
            opt.t_plate - csk_depth >= 0.6,
        )
    )

    # 10. head thickness is printable (>= 3 layers at 0.2 mm) and stiff enough
    checks.append(
        Check(
            "barb head thickness",
            opt.head_t,
            ">= 1.6",
            opt.head_t >= 1.6,
        )
    )

    return checks


def report(pedal: PedalProfile, board: BoardProfile, opt: PlateOptions) -> bool:
    checks = check_engagement(pedal, board, opt)
    print(f"\n{pedal.pedal_id}  (slot {board.slot_w} / rib {board.rib_w} / pitch {board.pitch})")
    for c in checks:
        print("  " + c.line())
    return all(c.ok for c in checks)


if __name__ == "__main__":
    import pathlib

    from .build import load_board, load_pedal

    root = pathlib.Path(__file__).resolve().parent.parent
    board, _ = load_board()
    ok = True
    for p in sorted((root / "catalog" / "pedals").glob("*.yaml")):
        pedal, _ = load_pedal(p)
        ok &= report(pedal, board, PlateOptions())
    raise SystemExit(0 if ok else 1)
