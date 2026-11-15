"""Draw the three candidate holder schemes for the Whammy V plate, to scale.

A design-review sheet, not a part: it answers "what do the holders look like" before any
of them is modelled in 3D. Each sheet carries a 1:1 plan of the whole part with the pedal,
the treadle, the printed no-go zones and all five OEM screws in place, two 5:1 details of
one collar, and the trade-off in material.

One conclusion is shared by all three schemes and is the reason none of them is a single
printed piece: an OEM hex head lies flat on the pedal's top face, so the only face a holder
can grip is the head's top - and a collar can only reach that face by coming down from
above, after the pedal is sitting on the plate. Every holder here is therefore a separate
part, dropped on and held down by one M3 socket screw into a heat-set insert in the plate.
That is also what the Fulltone FT mounts the owner pointed at do.

    .venv/Scripts/python digitech_whammy_v/src/sketch_holders.py
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT / "cfg" / "digitech_whammy_v.json"
OUT = PROJECT / "dwg"

PX_MM = 6.0
DETAIL_PX_MM = 26.0

PEDAL_HW = 82.5  # half width, +X toward the button panel
PEDAL_HL = 98.5  # half depth, +Y toward the INPUT end
PLATE_HW = 89.0  # 6.5 mm ledge outboard of the pedal, 6 tall so it can hold the M2.5

COLLAR_DIA = 10.0
RECESS_DIA = 6.6
RECESS_DEPTH = 1.2
HEAD_DIA = 5.8
HEAD_H = 2.5
COLLAR_H = HEAD_H + RECESS_DEPTH  # 3.7: underside on the top face, roof on the head
TREADLE_CUT_X = -78.9  # 0.9 mm clear of the treadle plate's edge at -78.0

CLIP_ROWS = (75.5, -60.5)  # 23 and 159 mm from the board-corner (+Y, INPUT) end
CLIP_COLUMNS = (-38.0, 38.0)
WINDOW_W = 22.0
LOOP_D = 19.0

ARM_Y = (-95.0, -88.0)  # the D arm threads the 10.5 mm gap under the harmony labels

INK = (28, 28, 28)
GREY = (120, 120, 120)
HOLDER = (20, 100, 58)
CAP_FILL = (208, 230, 216)
BODY_FILL = (150, 196, 170)
FOOT_FILL = (120, 172, 144)
ZONE_FILL = (253, 236, 176)
ZONE_LINE = (198, 138, 0)
TREADLE_FILL = (216, 216, 216)
PLATE_TINT = (150, 186, 224, 86)
PLATE_LINE = (26, 84, 148)
SCREW = (30, 74, 160)
CLIP = (122, 92, 190)
CLIP_FILL = (238, 232, 250)

FONT = ImageFont.load_default(size=17)
FONT_SMALL = ImageFont.load_default(size=13)


@dataclass(frozen=True)
class Site:
    id: str
    x: float
    y: float

    @property
    def side(self) -> float:
        return 1.0 if self.x > 0 else -1.0


class Sheet:
    """A millimetre canvas with y pointing up."""

    def __init__(self, x0, x1, y0, y1, px=PX_MM, pad=8):
        self.px = px
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.pad = pad
        self.w = int((x1 - x0) * px) + 2 * pad
        self.h = int((y1 - y0) * px) + 2 * pad
        self.img = Image.new("RGB", (self.w, self.h), (255, 255, 255))
        self.d = ImageDraw.Draw(self.img)

    def p(self, x, y):
        return ((x - self.x0) * self.px + self.pad, (self.y1 - y) * self.px + self.pad)

    def layer(self) -> Sheet:
        """A transparent copy on the same canvas, for see-through drawing."""
        s = Sheet(self.x0, self.x1, self.y0, self.y1, px=self.px, pad=self.pad)
        s.img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        s.d = ImageDraw.Draw(s.img)
        return s

    def over(self, other: Sheet) -> None:
        self.img = Image.alpha_composite(self.img.convert("RGBA"), other.img).convert("RGB")
        self.d = ImageDraw.Draw(self.img)

    def rect(self, x0, y0, x1, y1, fill=None, outline=INK, width=2):
        self.d.rectangle([*self.p(x0, y1), *self.p(x1, y0)], fill=fill, outline=outline,
                         width=width)

    def rounded(self, x0, y0, x1, y1, r, fill=None, outline=INK, width=2):
        self.d.rounded_rectangle([*self.p(x0, y1), *self.p(x1, y0)], radius=r * self.px,
                                 fill=fill, outline=outline, width=width)

    def box(self, x, y, dia):
        ax, ay = self.p(x, y)
        r = dia / 2.0 * self.px
        return [ax - r, ay - r, ax + r, ay + r]

    def circle(self, x, y, dia, fill=None, outline=INK, width=2):
        self.d.ellipse(self.box(x, y, dia), fill=fill, outline=outline, width=width)

    def chord(self, x, y, dia, keep_x_below, fill=None, outline=INK, width=2):
        """The part of a circle outboard of a vertical cut, cut square to the face."""
        ax, _ = self.p(x, y)
        cut, _ = self.p(keep_x_below, y)
        r = dia / 2.0 * self.px
        frac = max(-1.0, min(1.0, (cut - ax) / r))
        a = math.degrees(math.acos(frac))
        self.d.chord(self.box(x, y, dia), a, 360.0 - a, fill=fill, outline=outline,
                     width=width)

    def line(self, pts, fill=INK, width=2):
        self.d.line([self.p(x, y) for x, y in pts], fill=fill, width=width)

    def text(self, x, y, s, fill=INK, anchor="lm", font=FONT_SMALL):
        self.d.text(self.p(x, y), s, fill=fill, anchor=anchor, font=font)


def load() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def sites(cfg: dict) -> dict[str, Site]:
    return {
        k: Site(k, v["x_mm"], v["y_mm"])
        for k, v in cfg["fasteners"]["oem_top_plate"]["sites"].items()
    }


# --------------------------------------------------------------------------- #
# what every scheme shares: the plate, the clips, the pedal
# --------------------------------------------------------------------------- #


def plate(layer: Sheet) -> None:
    layer.rounded(-PLATE_HW, -PEDAL_HL, PLATE_HW, PEDAL_HL, 8.0, fill=PLATE_TINT,
                  outline=PLATE_LINE, width=3)
    for cx in CLIP_COLUMNS:
        for cy in CLIP_ROWS:
            if cy > 0:
                y_a, y_b = cy - LOOP_D / 2 - 1.0, PEDAL_HL
            else:
                y_a, y_b = -PEDAL_HL, cy + LOOP_D / 2 + 1.0
            layer.rect(cx - WINDOW_W / 2, y_a, cx + WINDOW_W / 2, y_b, fill=(0, 0, 0, 0),
                       outline=PLATE_LINE, width=2)


def clip_arches(sheet: Sheet) -> None:
    for cx in CLIP_COLUMNS:
        for cy in CLIP_ROWS:
            sheet.rounded(cx - WINDOW_W / 2, cy - LOOP_D / 2, cx + WINDOW_W / 2,
                          cy + LOOP_D / 2, 8.0, fill=CLIP_FILL, outline=CLIP, width=3)
            sheet.circle(cx, cy, 6.0, fill=None, outline=CLIP, width=2)


def pedal(sheet: Sheet, cfg: dict) -> None:
    sheet.rounded(-PEDAL_HW, -PEDAL_HL, PEDAL_HW, PEDAL_HL, 6.35, fill=(252, 252, 252),
                  outline=GREY, width=2)
    sheet.rect(-78.0, -97.6, 7.1, 97.6, fill=TREADLE_FILL, outline=GREY, width=1)
    sheet.text(-36.0, 2.0, "TREADLE", fill=(110, 110, 110), anchor="mm")
    sheet.text(-36.0, -4.0, "moves", fill=(110, 110, 110), anchor="mm")
    for zone in cfg["panel_zones"]["zones"]:
        x_lo, x_hi = zone["x_mm"]
        y_lo, y_hi = zone["y_mm"]
        sheet.rect(x_lo, y_lo, x_hi, y_hi, fill=ZONE_FILL, outline=ZONE_LINE, width=1)
        sheet.text(x_lo + 1.5, y_lo + 1.8, zone["id"].replace("_", " "),
                   fill=(150, 104, 0), anchor="lb")


def heads(sheet: Sheet, sm: dict[str, Site]) -> None:
    for s in sm.values():
        sheet.circle(s.x, s.y, HEAD_DIA, fill=SCREW, outline=SCREW, width=1)
        lx = s.x
        ly = s.y + 9.0
        sheet.text(lx, ly, s.id, fill=SCREW, anchor="mm", font=FONT)


# --------------------------------------------------------------------------- #
# the holder itself
# --------------------------------------------------------------------------- #


def collar(sheet: Sheet, s: Site, cut_x: float | None = None) -> None:
    """Ø10 collar, Ø6.6 x 1.2 recess, roof bearing on the head's top at 2.5."""
    if cut_x is None:
        sheet.circle(s.x, s.y, COLLAR_DIA, fill=CAP_FILL, outline=HOLDER, width=3)
    else:
        sheet.chord(s.x, s.y, COLLAR_DIA, cut_x, fill=CAP_FILL, outline=HOLDER, width=3)
    sheet.circle(s.x, s.y, RECESS_DIA, fill=(255, 255, 255), outline=HOLDER, width=1)


def stalk(sheet: Sheet, s: Site, w: float, foot_len: float, r: float) -> None:
    """The wall that stands on the plate's 4.5 mm stripe, with its M3 pad at one end."""
    x0, x1 = sorted((s.side * PEDAL_HW, s.side * PLATE_HW))
    y0 = s.y - w / 2
    y1 = s.y + w / 2 + foot_len
    sheet.rounded(x0, y0, x1, y1, r, fill=BODY_FILL, outline=HOLDER, width=3)
    if foot_len:
        insert(sheet, (x0 + x1) / 2, s.y + w / 2 + foot_len / 2)


def insert(sheet: Sheet, x: float, y: float) -> None:
    """A heat-set insert in the plate's stripe: what the holder's one M3 pulls on."""
    sheet.circle(x, y, 2.8, fill=(255, 255, 255), outline=HOLDER, width=2)
    sheet.line([(x - 1.4, y), (x + 1.4, y)], fill=HOLDER, width=1)
    sheet.line([(x, y - 1.4), (x, y + 1.4)], fill=HOLDER, width=1)


def toe_arm(sheet: Sheet, s: Site) -> None:
    """D is 60 mm inboard of the panel edge, so it hangs off a rib along the toe end.

    The arm runs at y -95..-88, the 10.5 mm strip between the pedal's end wall and the
    harmony label block, so it crosses no legend and no button well.
    """
    x0, x1 = sorted((PEDAL_HW, PLATE_HW))
    sheet.rect(s.x, ARM_Y[0], PEDAL_HW, ARM_Y[1], fill=CAP_FILL, outline=HOLDER, width=3)
    sheet.rounded(x0, ARM_Y[0], x1, ARM_Y[1], 3.5, fill=BODY_FILL, outline=HOLDER, width=3)
    insert(sheet, (x0 + x1) / 2, sum(ARM_Y) / 2)
    collar(sheet, s)


def panel_side(sheet: Sheet, sm: dict[str, Site], w: float, r: float) -> None:
    for key in ("A", "B"):
        stalk(sheet, sm[key], w, 13.0, r)
        collar(sheet, sm[key])


def treadle_side(sheet: Sheet, sm: dict[str, Site], w: float, r: float) -> None:
    for key in ("C", "E"):
        stalk(sheet, sm[key], w, 13.0, r)
        collar(sheet, sm[key], cut_x=TREADLE_CUT_X)


# --------------------------------------------------------------------------- #
# the three schemes
# --------------------------------------------------------------------------- #


def scheme_a(sheet: Sheet, sm: dict[str, Site]) -> None:
    """One holder per screw: five pill-shaped stalks, the least material."""
    panel_side(sheet, sm, 11.0, 5.5)
    treadle_side(sheet, sm, 11.0, 5.5)
    toe_arm(sheet, sm["D"])


def scheme_b(sheet: Sheet, sm: dict[str, Site]) -> None:
    """Twofer: one rail per side, two collars each, plus a separate D arm."""
    for key, w in ((("A", "B"), 12.0), (("E", "C"), 12.0)):
        lo = min(sm[k].y for k in key) - w / 2 - 13.0
        hi = max(sm[k].y for k in key) + w / 2 + 13.0
        side = sm[key[0]].side
        x0, x1 = sorted((side * PEDAL_HW, side * PLATE_HW))
        sheet.rounded(x0, lo, x1, hi, 2.3, fill=BODY_FILL, outline=HOLDER, width=3)
        insert(sheet, (x0 + x1) / 2, lo + 6.5)
        insert(sheet, (x0 + x1) / 2, hi - 6.5)
        for k in key:
            if side > 0:
                collar(sheet, sm[k])
            else:
                collar(sheet, sm[k], cut_x=TREADLE_CUT_X)
    toe_arm(sheet, sm["D"])


def scheme_c(sheet: Sheet, sm: dict[str, Site]) -> None:
    """Fulltone-style blades: five blades 14 wide with R2.3 shoulders."""
    panel_side(sheet, sm, 14.0, 2.3)
    treadle_side(sheet, sm, 14.0, 2.3)
    toe_arm(sheet, sm["D"])


SCHEMES = {
    "A": (scheme_a, "one holder per screw - five parts, the least material"),
    "B": (scheme_b, "twofer - one rail per side, two heads each, plus a D arm"),
    "C": (scheme_c, "Fulltone blades - five blades, 14 wide, R2.3 shoulders"),
}

NOTES = {
    "A": [
        "Five small parts, one per OEM head. Nothing spans between heads.",
        "Holder material about 16 cm3; the plate, about 92 cm3, is the same in all three.",
        "Least material and the most open look, and every collar is a plain circle with",
        "no shared rail to fight. Five parts to handle and five inserts to fit, though,",
        "and nothing braces one head against another.",
    ],
    "B": [
        "Two rails, one per side, each carrying two collars; D hangs off the panel rail.",
        "Three parts in all for five heads - the twofer idea.",
        "Holder material about 40 cm3 with the rails waisted between the collars.",
        "Stiffest by far: a stomped pedal cannot rock a rail, and the rails also shield",
        "the pedal's side edges. Most material, and the most visible from the front.",
    ],
    "C": [
        "Five 14-wide blades with R2.3 shoulders and a flat top - the shape of the Type",
        "FT1 tabs the owner pointed at, but climbed onto the top face of the pedal.",
        "Holder material about 21 cm3.",
        "Stiffer than A, because a 14-wide blade resists the pedal rocking more than an",
        "11-wide one, and it looks deliberate rather than improvised.",
    ],
}


# --------------------------------------------------------------------------- #
# details
# --------------------------------------------------------------------------- #


def detail_plan() -> Image.Image:
    s = Sheet(-8.0, 8.0, -8.5, 8.5, px=DETAIL_PX_MM)
    s.rect(-8.0, -8.5, PEDAL_HW - 78.3, 8.5, fill=(252, 252, 252), outline=GREY, width=2)
    s.rect(PEDAL_HW - 78.3, -8.5, 8.0, 8.5, fill=PLATE_TINT, outline=PLATE_LINE, width=2)
    s.rect(PEDAL_HW - 78.3, -6.0, 8.0, 6.0, fill=BODY_FILL, outline=HOLDER, width=2)
    collar(s, Site("A", 0.0, 0.0))
    s.circle(0.0, 0.0, HEAD_DIA, fill=SCREW, outline=SCREW, width=1)
    s.text(-7.6, 7.6, "5:1 plan", fill=GREY, anchor="lm", font=FONT)
    s.text(0.0, -4.4, "OEM head", fill=SCREW, anchor="mm")
    s.text(6.2, -4.2, "stalk", fill=HOLDER, anchor="mm")
    s.text(-7.6, -7.6, "pedal top face", fill=GREY, anchor="lm")
    return s.img


def detail_section() -> Image.Image:
    """4:1 section on the panel side: head, collar, roof contact and stalk."""
    s = Sheet(-9.0, 12.0, -14.0, 9.0, px=DETAIL_PX_MM)
    edge = PEDAL_HW - 78.3  # the pedal's side wall, 4.2 mm inboard of the collar's centre
    s.rect(-9.0, -14.0, edge, 0.0, fill=(248, 248, 248), outline=GREY, width=2)
    s.rect(edge, -14.0, 8.7, 0.0, fill=BODY_FILL, outline=HOLDER, width=3)
    s.line([(4.9, -13.2), (5.9, -11.6)], fill=INK, width=2)
    s.line([(6.3, -13.2), (7.3, -11.6)], fill=INK, width=2)
    s.rect(-5.0, 0.0, -3.3, COLLAR_H, fill=CAP_FILL, outline=HOLDER, width=3)
    s.rect(3.3, 0.0, 5.0, COLLAR_H, fill=CAP_FILL, outline=HOLDER, width=3)
    s.rect(-3.3, HEAD_H, 3.3, COLLAR_H, fill=CAP_FILL, outline=HOLDER, width=3)
    s.line([(-9.0, 0.0), (-5.0, 0.0)], fill=GREY, width=4)
    s.line([(-3.3, 0.0), (3.3, 0.0)], fill=GREY, width=2)
    s.line([(5.0, 0.0), (edge, 0.0)], fill=GREY, width=2)
    s.rect(-2.9, 0.0, 2.9, HEAD_H, fill=SCREW, outline=SCREW, width=2)
    s.rect(-1.3, HEAD_H - 0.6, 1.3, HEAD_H, fill=(255, 255, 255), outline=SCREW, width=1)
    s.text(-8.6, 1.4, "pedal top face", fill=GREY)
    s.text(0.0, 7.6, "roof bears on the head", fill=HOLDER, anchor="mm")
    s.line([(0.0, 6.6), (0.0, COLLAR_H + 0.3)], fill=HOLDER, width=1)
    s.text(-8.6, -1.6, "pedal", fill=GREY, anchor="lm", font=FONT)
    s.text(-8.6, -4.0, "side wall", fill=GREY, anchor="lm")
    s.text(9.4, -1.0, "stalk", fill=HOLDER, anchor="lm")
    s.text(-8.6, -12.6, "44.7 mm down", fill=HOLDER, anchor="lm")
    s.text(-8.6, -13.8, "to the plate", fill=HOLDER, anchor="lm")
    return s.img


# --------------------------------------------------------------------------- #
# sheet assembly
# --------------------------------------------------------------------------- #


def build(key: str) -> None:
    build_fn, subtitle = SCHEMES[key]
    cfg = load()
    sm = sites(cfg)

    plan = Sheet(-104.0, 104.0, -112.0, 112.0)
    pedal(plan, cfg)
    top = plan.layer()
    plate(top)
    plan.over(top)
    clip_arches(plan)
    build_fn(plan, sm)
    heads(plan, sm)

    left = detail_plan()
    right = detail_section()
    detail_w = left.width + 60 + right.width
    width = max(plan.w, detail_w + 80, 1240)

    head_h = 70
    notes = NOTES[key]
    height = head_h + plan.h + 12 + max(left.height, right.height) + 44 + 24 * len(notes) + 24
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    canvas.paste(plan.img, ((width - plan.w) // 2, head_h))
    d = ImageDraw.Draw(canvas)

    d.text((34, 16), f"Whammy V  -  holder scheme {key}", fill=INK, font=FONT)
    d.text((34, 44), f"{subtitle}.   1:1 plan, mm.  Grey = pedal, blue = plate, "
                     "purple = QuickMount clip.", fill=HOLDER, font=FONT_SMALL)

    y = head_h + plan.h + 12
    x = (width - detail_w) // 2
    canvas.paste(left, (x, y))
    canvas.paste(right, (x + left.width + 60, y))

    y = y + max(left.height, right.height) + 34
    for i, line in enumerate(notes):
        d.text((34, y + i * 24), line, fill=INK, font=FONT_SMALL)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"sketch_holders_{key}.png"
    canvas.save(path)
    print("wrote", path, canvas.size)


def main() -> int:
    for key in SCHEMES:
        build(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
