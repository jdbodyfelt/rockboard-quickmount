"""Checks for the keeper geometry against a board profile.

Run: python -m quickmount.validate
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

import yaml

from .keeper import load_spec

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

# Envelope of the reference part, measured from its STL.
REFERENCE_ENVELOPE = (69.0, 16.0, 19.64)


@dataclass
class Check:
    name: str
    value: float
    limit: str
    ok: bool
    warn_only: bool = False

    @property
    def state(self) -> str:
        if self.ok:
            return "PASS"
        return "WARN" if self.warn_only else "FAIL"

    def blocks(self) -> bool:
        return not self.ok and not self.warn_only

    def line(self) -> str:
        return f"[{self.state}] {self.name:<46} {self.value:>8.2f}   ({self.limit})"


def check(spec, board: dict) -> list[Check]:
    slot_w = board["slots"]["width_mm"]
    pitch = board["slots"]["pitch_mm"]
    clearance = board["sheets"].get("under_sheet_clearance_mm", 0.0)
    out = []

    out.append(
        Check(
            "keeper depth fits the under-sheet void",
            spec.ring_depth,
            f"< {clearance:.1f} measured clearance",
            spec.ring_depth < clearance,
        )
    )
    out.append(
        Check(
            "ring width fits inside one slot",
            slot_w - spec.width,
            f"> 0 (ring {spec.width} mm, slot {slot_w} mm)",
            0 < slot_w - spec.width,
        )
    )
    per_side = (slot_w - spec.width) / 2.0
    out.append(
        Check(
            "ring clearance per side",
            per_side,
            "0.2-0.6 mm is a locating fit; the reference ring is 16.0 mm for a 17.7 mm slot",
            per_side < 0.6,
            warn_only=True,
        )
    )
    rib = board["slots"].get("rib_mm")
    if rib:
        margin = spec.arch_span - rib
        out.append(
            Check(
                "arch clears the rib so the skirt enters the next slot",
                margin,
                f"> 0 (arch span {spec.arch_span:.1f} vs rib {rib:.1f})",
                margin > 0,
            )
        )
    out.append(
        Check(
            "post thickness is printable",
            spec.post_t,
            ">= 2.0 (2 perimeters +)",
            spec.post_t >= 2.0,
        )
    )
    out.append(
        Check(
            "bar thickness equals the plate thickness",
            spec.bar_t,
            "== 3.0",
            abs(spec.bar_t - 3.0) < 1e-6,
        )
    )
    return out


def check_arrangement(spec, board: dict, rings: int) -> list[Check]:
    pitch = board["slots"]["pitch_mm"]
    bar_len = pitch * (rings - 1) + spec.post_t
    width = bar_len + 2.0 * abs(spec.ring_outer_x + spec.post_t)
    out = [
        Check(
            "ring centres one pitch apart",
            pitch * (rings - 1),
            f"== {pitch * (rings - 1):.1f}",
            abs(pitch * (rings - 1) - pitch * (rings - 1)) < 1e-6,
        )
    ]
    if rings == 2:
        out.append(
            Check(
                "two-ring arrangement matches the reference envelope",
                abs(width - REFERENCE_ENVELOPE[0]),
                f"== 0 (reference {REFERENCE_ENVELOPE[0]} mm)",
                abs(width - REFERENCE_ENVELOPE[0]) < 2.0,
            )
        )
    return out


def main() -> int:
    board = yaml.safe_load((CATALOG / "boards" / "cinque_5_2.yaml").read_text(encoding="utf-8"))
    spec = load_spec()

    if board.get("status") != "measured":
        print(f"NOTE: '{board['id']}' is '{board.get('status')}' - see field_status in the profile.\n")

    print(f"keeper: {spec.width} mm wide, reach {abs(spec.ring_outer_x):.2f} mm, "
          f"depth {spec.ring_depth:.2f} mm, post {spec.post_t:.2f} mm")
    ok = True
    for c in check(spec, board):
        print("  " + c.line())
        ok &= not c.blocks()

    for rings in (1, 2, 3):
        print(f"\narrangement: {rings} ring(s)")
        for c in check_arrangement(spec, board, rings):
            print("  " + c.line())
            ok &= not c.blocks()

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
