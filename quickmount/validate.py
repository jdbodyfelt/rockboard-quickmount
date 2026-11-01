"""Checks for the clip geometry against a board profile.

Run: python -m quickmount.validate
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

import yaml

from .clip import load_profile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"


@dataclass
class Check:
    name: str
    value: float
    limit: str
    ok: bool

    def line(self) -> str:
        state = "PASS" if self.ok else "FAIL"
        return f"[{state}] {self.name:<44} {self.value:>8.2f}   ({self.limit})"


def load_board(name: str = "cinque_5_2") -> dict:
    return yaml.safe_load((CATALOG / "boards" / f"{name}.yaml").read_text(encoding="utf-8"))


def check(profile, board: dict) -> list[Check]:
    slot_w = board["slots"]["width_mm"]
    pitch = board["slots"]["pitch_mm"]
    sheet_t = board["sheets"]["aluminium_mm"] + board["sheets"]["powder_coat_mm"]
    clearance = board["sheets"]["under_sheet_clearance_mm"]

    hook_c = profile.hook_centres_x
    spacing = hook_c[1] - hook_c[0]
    span = profile.span_x
    scale = (pitch / 2.0) / hook_c[1]
    out = []

    out.append(
        Check(
            "hook spacing scaled to one slot pitch",
            spacing * scale,
            f"== {pitch:.1f} (measured {spacing:.2f}, scale {scale:.4f})",
            abs(spacing * scale - pitch) < 0.01 and abs(scale - 1.0) < 0.10,
        )
    )
    out.append(
        Check(
            "hook depth fits the board void",
            profile.depth_below_bar,
            f"< {clearance:.1f} under-sheet clearance",
            profile.depth_below_bar < clearance,
        )
    )
    out.append(
        Check(
            "overall width matches the reference",
            span[1] - span[0],
            "69.0 mm as measured",
            abs((span[1] - span[0]) - 69.0) < 0.5,
        )
    )
    out.append(
        Check(
            "clip width fits inside one slot",
            slot_w - profile.width,
            f"> 0 (clip {profile.width} mm, slot {slot_w} mm)",
            0 < slot_w - profile.width,
        )
    )
    print(
        f"  note: sheet {sheet_t:.2f} mm vs the reference bar-to-skirt gap of "
        "1.82 mm - the reference part clamps loosely; verify on the board"
    )
    return out


def check_plate(profile, board: dict, plate_w: float, stations, screw_xy, head_od: float):
    out = []
    span = profile.span_x
    overhang = max(span[1], -span[0]) - plate_w / 2.0
    out.append(
        Check(
            "hook overhang beyond plate edge",
            overhang,
            "informational (hooks sit below the plate, inside the void)",
            True,
        )
    )
    hook_half = profile.width / 2.0
    clear = min(
        min(abs(y - sy) for _, sy in screw_xy) - (hook_half + head_od / 2.0) for y in stations
    )
    out.append(Check("hook line clear of pedal screws", clear, "> 0", clear > 0))
    return out


def main() -> int:
    board = load_board()
    profile = load_profile()

    if board.get("status") != "measured":
        print(
            f"NOTE: '{board['id']}' is '{board.get('status')}'. Slot width, rib, pitch and\n"
            "      sheet thickness are provisional until measured with callipers.\n"
        )

    print(
        f"clip: {profile.width} mm wide, {profile.depth_below_bar:.2f} mm deep, "
        f"hooks at {profile.hook_centres_x[0]:.2f} / {profile.hook_centres_x[1]:.2f} mm"
    )
    ok = True
    for c in check(profile, board):
        print("  " + c.line())
        ok &= c.ok

    for path in sorted((CATALOG / "pedals").glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        w = raw["physical"]["width_mm"]
        d = raw["physical"]["depth_mm"]
        inset = raw["pedal_screws"]["inset_mm"]
        hx, hy = w / 2.0 - inset, d / 2.0 - inset
        screws = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
        y = (d - 1.0) / 2.0 - 24.0
        print(f"\n{raw['id']}")
        for c in check_plate(profile, board, w - 1.0, (-y, y), screws,
                             raw["pedal_screws"]["head_od_mm"]):
            print("  " + c.line())
            ok &= c.ok

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
