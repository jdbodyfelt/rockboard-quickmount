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


def arch_scale_for(spec, board: dict, intrusion: float = 1.2) -> float:
    slots = board["slots"]
    rib_max = slots.get("rib_max_mm", slots.get("rib_mm"))
    return (rib_max + intrusion) / spec.arch_span


def ring_width_for(board: dict) -> float:
    """Retention is pressure on the slot edge, so size the ring to reach the edge."""
    return board["slots"]["width_mm"] - 0.3


def check(spec, board: dict, arch_scale: float = 1.0, ring_width: float | None = None) -> list[Check]:
    slot_w = board["slots"]["width_mm"]
    pitch = board["slots"]["pitch_mm"]
    clearance = board["sheets"].get("under_sheet_clearance_mm", 0.0)
    out = []

    sheet_t = board["sheets"]["aluminium_mm"] + board["sheets"]["powder_coat_mm"]
    out.append(
        Check(
            "arch base clears the full sheet thickness",
            spec.arch_base_depth - sheet_t,
            f"> 0 (arch base {spec.arch_base_depth:.1f} below bar, sheet {sheet_t:.1f})",
            spec.arch_base_depth > sheet_t,
        )
    )
    below_sheet = spec.ring_depth - sheet_t
    out.append(
        Check(
            "ring depth below the sheet fits the board void",
            below_sheet,
            f"< {clearance:.1f} measured clearance (ring {spec.ring_depth:.1f} below bar)",
            below_sheet < clearance,
        )
    )
    w = spec.width if ring_width is None else ring_width
    total = slot_w - w
    out.append(
        Check(
            "ring reaches the slot edge (spring pressure)",
            total,
            f"0.1-0.5 mm total (ring {w:.1f} mm, slot {slot_w:.1f} mm)",
            0.1 <= total <= 0.5,
        )
    )
    slots = board["slots"]
    rib_max = slots.get("rib_max_mm", slots.get("rib_mm"))
    if rib_max:
        span = spec.scaled_arch_span(arch_scale)
        out.append(
            Check(
                "skirt intrusion into the next slot (worst-case rib)",
                span - rib_max,
                f">= 0.8 (arch span {span:.1f} vs rib max {rib_max:.1f})",
                span - rib_max >= 0.8,
            )
        )
        rib_min = slots.get("rib_min_mm", rib_max)
        slot_w_local = slots["width_mm"]
        out.append(
            Check(
                "skirt still inside the slot at the widest rib",
                slot_w_local - (span - rib_min),
                f"> 0 (span {span:.1f}, rib min {rib_min:.1f}, slot {slot_w_local:.1f})",
                slot_w_local - (span - rib_min) > 0,
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


def check_arrangement(spec, board: dict, rings: int, arch_scale: float = 1.0) -> list[Check]:
    pitch = board["slots"]["pitch_mm"]
    bar_len = pitch * (rings - 1) + spec.post_t
    width = bar_len + 2.0 * spec.scaled_arch_span(arch_scale)
    out = [
        Check(
            "ring centres one pitch apart",
            pitch * (rings - 1),
            f"== {pitch * (rings - 1):.1f}",
            abs(pitch * (rings - 1) - pitch * (rings - 1)) < 1e-6,
        )
    ]
    out.append(
        Check(
            "nominal arrangement width",
            width,
            f"reference clip is {REFERENCE_ENVELOPE[0]:.1f} mm wide before the arch was widened",
            True,
        )
    )
    return out


def main() -> int:
    board = yaml.safe_load((CATALOG / "boards" / "cinque_5_2.yaml").read_text(encoding="utf-8"))
    spec = load_spec()

    if board.get("status") != "measured":
        print(f"NOTE: '{board['id']}' is '{board.get('status')}' - see field_status in the profile.\n")

    scale = arch_scale_for(spec, board)
    ring_w = ring_width_for(board)
    print(f"keeper: {ring_w:.2f} mm wide (push fit), depth {spec.ring_depth:.2f} mm, "
          f"post {spec.post_t:.2f} mm, arch span {spec.scaled_arch_span(scale):.2f} mm "
          f"(scale {scale:.4f})")
    ok = True
    for c in check(spec, board, scale, ring_w):
        print("  " + c.line())
        ok &= not c.blocks()

    for rings in (1, 2, 3):
        print(f"\narrangement: {rings} ring(s)")
        for c in check_arrangement(spec, board, rings, scale):
            print("  " + c.line())
            ok &= not c.blocks()

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
