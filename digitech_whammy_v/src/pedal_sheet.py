"""Draw the pedal and render the mount, straight from the config.

Three jobs, in the order they are useful:

1. ``ref/pedal_sheet.png``  - an external drawing of the **device itself**: plan, side
   elevation and end elevation, dimensioned, with the treadle's sweep marked. This is the
   sheet to hold calipers against.
2. ``dwg/render_pedal.png`` - the pedal check model alone.
3. ``dwg/render_cage.png``  - the printed set alone: basket, ring, clips.
4. ``dwg/render_pedal_in_cage.png`` - the two together, which is the fit check the eye
   wants to do.

Everything is read from ``cfg/digitech_whammy_v.json``, so the drawings, the renders and
the parts cannot drift apart. The pedal is a *checking* model: envelope, top-face plane,
pads, OEM heads and the treadle on its hinge. It is not a copy of the pedal.

    .venv/Scripts/python digitech_whammy_v/src/pedal_sheet.py
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "digitech_whammy_v" / "src"))

import quickmount_whammy_v as qm

CONFIG = PROJECT / "cfg" / "digitech_whammy_v.json"
REF = PROJECT / "ref"
DWG = PROJECT / "dwg"

PX = 4.0
INK = (24, 24, 24)
THIN = (110, 110, 110)
DIM = (150, 40, 40)
SWEEP = (40, 130, 80)
BLUE = (26, 84, 148)
FILL_BODY = (238, 238, 238)
FILL_TREADLE = (206, 206, 206)
FILL_SWEEP = (216, 236, 222)
ZONE = (253, 236, 176)
ZONE_LINE = (198, 138, 0)

FONT_T = ImageFont.load_default(size=26)
FONT = ImageFont.load_default(size=16)
FONT_S = ImageFont.load_default(size=13)


class View:
    """A self-contained panel in model millimetres, y up, pasted onto the sheet."""

    def __init__(self, x0, x1, y0, y1, px=PX, pad=8):
        self.px = px
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.pad = pad
        self.w = int((x1 - x0) * px) + 2 * pad
        self.h = int((y1 - y0) * px) + 2 * pad
        self.img = Image.new("RGB", (self.w, self.h), (255, 255, 255))
        self.d = ImageDraw.Draw(self.img)

    def p(self, x, y):
        return ((x - self.x0) * self.px + self.pad, (self.y1 - y) * self.px + self.pad)

    def rect(self, x0, y0, x1, y1, fill=None, outline=INK, width=1):
        self.d.rectangle([*self.p(x0, y1), *self.p(x1, y0)], fill=fill, outline=outline,
                         width=width)

    def round_rect(self, x0, y0, x1, y1, r, fill=None, outline=INK, width=1):
        self.d.rounded_rectangle([*self.p(x0, y1), *self.p(x1, y0)], radius=r * self.px,
                                 fill=fill, outline=outline, width=width)

    def line(self, pts, fill=INK, width=1):
        self.d.line([self.p(x, y) for x, y in pts], fill=fill, width=width)

    def circle(self, x, y, dia, fill=None, outline=INK, width=1):
        ax, ay = self.p(x, y)
        r = dia / 2 * self.px
        self.d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=fill, outline=outline,
                       width=width)

    def text(self, x, y, s, fill=INK, font=FONT_S, anchor="lm"):
        self.d.text(self.p(x, y), s, fill=fill, font=font, anchor=anchor)

    def arc(self, x, y, r_mm, start_deg, end_deg, fill=SWEEP, width=2):
        ax, ay = self.p(x, y)
        r = r_mm * self.px
        self.d.arc([ax - r, ay - r, ax + r, ay + r], -end_deg, -start_deg, fill=fill,
                   width=width)

    def dim_h(self, x0, x1, y, label, tick=6.0, fill=DIM):
        self.line([(x0, y), (x1, y)], fill=fill)
        for x, s in ((x0, 1.0), (x1, -1.0)):
            self.line([(x, y), (x + s * 2.2, y + 1.1)], fill=fill)
            self.line([(x, y), (x + s * 2.2, y - 1.1)], fill=fill)
        for x in (x0, x1):
            self.line([(x, y), (x, y - tick)], fill=fill)
        self.text((x0 + x1) / 2, y - 1.2, label, fill=fill, font=FONT, anchor="mb")

    def dim_v(self, y0, y1, x, label, fill=DIM):
        self.line([(x, y0), (x, y1)], fill=fill)
        for y, s in ((y0, 1.0), (y1, -1.0)):
            self.line([(x, y), (x + 1.1, y + s * 2.2)], fill=fill)
            self.line([(x, y), (x - 1.1, y + s * 2.2)], fill=fill)
        self.text(x - 1.4, (y0 + y1) / 2, label, fill=fill, font=FONT, anchor="rm")


def load() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _rotate(y, z, hinge_y, hinge_z, deg):
    import math
    dy, dz = y - hinge_y, z - hinge_z
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (dy * c - dz * s + hinge_y, dy * s + dz * c + hinge_z)


# --------------------------------------------------------------------------- #
# the three views of the device
# --------------------------------------------------------------------------- #


def view_plan(cfg: dict) -> View:
    ped, tr = cfg["physical"], cfg["treadle"]
    hw, hd = ped["width_mm"] / 2, ped["depth_mm"] / 2
    tx0, tx1 = tr["footprint_x_mm"]
    sx0, sx1 = tr["sweep_x_mm"]
    v = View(-hw - 26.0, hw + 26.0, -hd - 26.0, hd + 22.0)

    v.rect(sx0, -hd, sx1, hd, fill=FILL_SWEEP)
    v.round_rect(-hw, -hd, hw, hd, ped["corner_radius_mm"], fill=FILL_BODY,
                 outline=INK, width=2)
    v.rect(tx0, -hd, tx1, hd, fill=FILL_TREADLE, outline=THIN, width=2)
    for zone in cfg["panel_zones"]["zones"]:
        zx0, zx1 = zone["x_mm"]
        zy0, zy1 = zone["y_mm"]
        v.rect(zx0, zy0, zx1, zy1, fill=ZONE, outline=ZONE_LINE)
    for sx in (-1, 1):
        for sy in (-1, 1):
            v.circle(sx * cfg["feet"]["x_mm"], sy * cfg["feet"]["y_mm"],
                     cfg["feet"]["dia_mm"], outline=THIN)
    for key, (px, py) in qm.load().sites.items():
        v.circle(px, py, cfg["fasteners"]["oem_top_plate"]["head_dia_mm"],
                 fill=(30, 74, 160), outline=(30, 74, 160))
        v.text(px, py + 7.0, key, fill=(30, 74, 160), font=FONT, anchor="mm")

    v.dim_h(-hw, hw, -hd - 12.0, f"{ped['width_mm']:.1f}")
    v.dim_v(-hd, hd, -hw - 12.0, f"{ped['depth_mm']:.1f}")
    v.dim_v(-hd, hd, hw + 12.0, "197.0")
    v.dim_h(tx0, tx1, hd + 10.0, f"{tx1 - tx0:.1f}")
    v.text((tx0 + tx1) / 2, -hd + 13.0, "treadle, measured", fill=THIN, anchor="mm")
    v.text((sx1 + tx1) / 2, -hd + 7.0, "sweep margin", fill=SWEEP, anchor="mm")
    return v


def view_side(cfg: dict) -> View:
    ped, tr = cfg["physical"], cfg["treadle"]
    hd = ped["depth_mm"] / 2
    plate = cfg["quickmount"]["plate"]["thickness_mm"]
    z0, z1 = tr["underside_z_mm"] - plate, tr["top_z_mm"] - plate
    base = -9.0
    hy, hz = tr["hinge"]["y_mm"], tr["hinge"]["z_mm"] - plate
    v = View(-hd - 24.0, hd + 24.0, base - 18.0, z1 + 24.0)

    v.rect(-hd, base, hd, z0, fill=FILL_BODY, outline=INK, width=2)
    # the treadle spans the full depth, so in this view it is a long plate on its hinge
    plate = [(-hd, z0), (hd, z0), (hd, z1), (-hd, z1)]
    v.line(plate + [plate[0]], fill=INK, width=2)
    v.text(-hd + 8.0, (z0 + z1) / 2, "treadle at rest", fill=THIN)

    # its travel, drawn as a sweep from the hinge rather than a second position: the toe
    # drops into the pedal's own recess, so a second outline would just cross the body
    v.arc(hy, hz, 30.0, 180.0, 180.0 + tr["sweep_deg"][1])
    tip = _rotate(hy - 30.0, hz, hy, hz, tr["sweep_deg"][1])
    v.line([(hy - 30.0, hz), tip], fill=SWEEP, width=2)
    v.text(hy - 34.0, hz + 4.0, f"{tr['sweep_deg'][1]:.0f} deg", fill=SWEEP, anchor="rm")
    v.text(-hd + 8.0, z0 - 12.0,
           f"toe travels {tr['sweep_deg'][1]:.0f} deg down into the pedal's recess",
           fill=SWEEP)
    v.circle(hy, hz, 5.0, fill=(255, 255, 255), outline=DIM, width=2)
    v.text(hy - 4.0, hz + 6.0, "hinge", fill=DIM, anchor="rm")

    v.dim_v(base, z0, -hd - 12.0, f"{z0 - base:.1f}", )
    v.dim_v(z0, z1, hd + 12.0, f"{z1 - z0:.1f}")
    v.dim_h(-hd, hd, base - 12.0, f"{ped['depth_mm']:.1f}")
    return v


def view_end(cfg: dict) -> View:
    ped, tr = cfg["physical"], cfg["treadle"]
    hw = ped["width_mm"] / 2
    plate = cfg["quickmount"]["plate"]["thickness_mm"]
    z0, z1 = tr["underside_z_mm"] - plate, tr["top_z_mm"] - plate
    base = -9.0
    tx0, tx1 = tr["footprint_x_mm"]
    v = View(-hw - 24.0, hw + 24.0, base - 18.0, z1 + 24.0)

    v.rect(-hw, base, hw, z0, fill=FILL_BODY, outline=INK, width=2)
    for sx in (-1, 1):
        v.rect(sx * cfg["feet"]["x_mm"] - 6.5, base - cfg["feet"]["height_mm"],
               sx * cfg["feet"]["x_mm"] + 6.5, base, outline=THIN)
    v.rect(tx0, z0, tx1, z1, fill=FILL_TREADLE, outline=THIN, width=2)
    v.dim_h(tx0, tx1, z1 + 7.0, f"{tx1 - tx0:.1f}")
    v.dim_h(-hw, hw, base - 12.0, f"{ped['width_mm']:.1f}")
    v.dim_v(z0, z1, hw + 12.0, f"{z1 - z0:.1f}")
    return v


# --------------------------------------------------------------------------- #
# views of the mount
# --------------------------------------------------------------------------- #


def view_mount_plan(cfg: dict, spec) -> View:
    q = cfg["quickmount"]
    bk, rg = cfg["basket"], cfg["ring"]
    hx, hy = q["plate"]["x_mm"] / 2, q["plate"]["y_mm"] / 2
    ped = cfg["physical"]
    v = View(-hx - 30.0, hx + 30.0, -hy - 24.0, hy + 30.0)

    # the pedal, for context only
    v.round_rect(-ped["width_mm"] / 2, -ped["depth_mm"] / 2, ped["width_mm"] / 2,
                 ped["depth_mm"] / 2, ped["corner_radius_mm"], outline=(200, 200, 200))

    # basket: walls, windows, closed clip slots
    v.round_rect(-hx, -hy, hx, hy, q["plate"]["corner_radius_mm"], fill=(232, 240, 250),
                 outline=BLUE, width=2)
    wx0, wx1 = bk["inner_x_mm"], bk["inner_x_mm"] + bk["wall_thickness_mm"]
    wy0, wy1 = bk["inner_y_mm"], bk["inner_y_mm"] + bk["wall_thickness_mm"]
    for x0, x1 in ((-wx1, -wx0), (wx0, wx1)):
        v.rect(x0, -hy, x1, hy, fill=(206, 224, 244), outline=BLUE)
    for y0, y1 in ((-wy1, -wy0), (wy0, wy1)):
        v.rect(-wx0, y0, wx0, y1, fill=(206, 224, 244), outline=BLUE)
    for w in bk["windows"]:
        half = bk["wall_thickness_mm"] / 2
        if w["wall"] in ("+x", "-x"):
            x = (1 if w["wall"] == "+x" else -1) * (bk["inner_x_mm"] + half)
            v.round_rect(x - half, w["centre_y_mm"] - w["length_mm"] / 2, x + half,
                         w["centre_y_mm"] + w["length_mm"] / 2, half, fill=(255, 255, 255),
                         outline=BLUE)
        else:
            y = (1 if w["wall"] == "+y" else -1) * (bk["inner_y_mm"] + half)
            v.round_rect(w["centre_x_mm"] - w["length_mm"] / 2, y - half,
                         w["centre_x_mm"] + w["length_mm"] / 2, y + half, half,
                         fill=(255, 255, 255), outline=BLUE)
    gap = q["clips"]["tool_gap_mm"]
    for cx in q["clips"]["columns_x_mm"]:
        for cy in q["clips"]["rows_y_mm"]:
            sign = 1.0 if cy > 0 else -1.0
            mouth = cy - sign * spec.section.half_mouth_mm
            end = sign * (abs(cy) + spec.section.half_outer_mm + gap)
            y0, y1 = sorted((mouth, end))
            v.round_rect(cx - q["clips"]["width_mm"] / 2, y0,
                         cx + q["clips"]["width_mm"] / 2, y1, 4.0, outline=BLUE)

    # ring: outer band, lips on four sides, cups
    v.round_rect(-hx, -hy, hx, hy, q["plate"]["corner_radius_mm"], outline=(20, 100, 58),
                 width=2)
    v.rect(rg["inner_x_treadle_mm"], -rg["treadle_column_y_mm"],
           rg["treadle_column_x_mm"], rg["treadle_column_y_mm"], outline=(20, 100, 58),
           width=2)
    v.rect(rg["treadle_column_x_mm"], rg["lip_y_mm"][0], rg["inner_x_panel_mm"],
           rg["lip_y_mm"][1], outline=(20, 100, 58), width=2)
    for notch in rg["notches"]:
        v.rect(notch["x_mm"][0], notch["y_mm"][0], notch["x_mm"][1], notch["y_mm"][1],
               outline=(20, 100, 58))
    for key, (px, py) in spec.sites.items():
        v.circle(px, py, spec.collar_dia_mm, outline=(20, 100, 58), width=2)
        v.circle(px, py, spec.head_dia_mm, fill=(30, 74, 160), outline=(30, 74, 160))
        v.text(px, py + 7.5, key, fill=(30, 74, 160), font=FONT, anchor="mm")
    for x, y in [(float(a), float(b)) for a, b in rg["screws"]["stations"]]:
        v.circle(x, y, 6.4, outline=(150, 40, 40), width=2)
        v.circle(x, y, 3.4, fill=(255, 255, 255), outline=(150, 40, 40))

    v.dim_h(-hx, hx, -hy - 12.0, f"{q['plate']['x_mm']:.0f}")
    v.dim_v(-hy, hy, -hx - 14.0, f"{q['plate']['y_mm']:.0f}")
    v.dim_h(q["clips"]["columns_x_mm"][0], q["clips"]["columns_x_mm"][1], hy + 12.0,
            f"{q['clips']['columns_x_mm'][1] - q['clips']['columns_x_mm'][0]:.0f} = 1 column")

    return v


def view_mount_end(cfg: dict, spec) -> View:
    q = cfg["quickmount"]
    bk, rg = cfg["basket"], cfg["ring"]
    hx = q["plate"]["x_mm"] / 2
    ped = cfg["physical"]
    t = q["plate"]["thickness_mm"]
    z_top, z_ring = bk["top_z_mm"], rg["top_z_mm"]
    v = View(-hx - 48.0, hx + 26.0, -26.0, z_ring + 26.0)

    v.rect(-hx, 0.0, hx, t, fill=(232, 240, 250), outline=BLUE, width=2)
    wx0, wx1 = bk["inner_x_mm"], bk["inner_x_mm"] + bk["wall_thickness_mm"]
    for x0, x1 in ((-wx1, -wx0), (wx0, wx1)):
        v.rect(x0, 0.0, x1, z_top, fill=(206, 224, 244), outline=BLUE, width=2)
    v.rect(-hx, z_top, hx, z_ring, fill=(214, 236, 220), outline=(20, 100, 58), width=2)
    v.rect(-hx, z_top, -wx1, z_ring, fill=(255, 255, 255), outline=(20, 100, 58))
    v.rect(wx1, z_top, hx, z_ring, fill=(255, 255, 255), outline=(20, 100, 58))

    # pedal body and the treadle above it, for the height story
    v.rect(-ped["width_mm"] / 2, t + 0.2, ped["width_mm"] / 2, z_top,
           outline=(200, 200, 200))
    tr = cfg["treadle"]
    v.rect(tr["footprint_x_mm"][0], z_top, tr["footprint_x_mm"][1], tr["top_z_mm"],
           fill=(236, 236, 236), outline=(150, 150, 150))

    for cx in q["clips"]["columns_x_mm"]:
        v.rect(cx - 9.5, -15.89, cx + 9.5, t, fill=(238, 232, 250),
               outline=(122, 92, 190), width=2)
    v.dim_v(0.0, z_top, -hx - 14.0, f"{z_top:.1f}")
    v.dim_v(0.0, z_ring, hx + 12.0, f"{z_ring:.1f}")
    v.dim_v(-15.89, 0.0, -hx - 28.0, "15.89")
    v.dim_h(-hx, hx, -18.0, f"{q['plate']['x_mm']:.0f}")
    return v


# --------------------------------------------------------------------------- #
# the sheet
# --------------------------------------------------------------------------- #


def device_sheet(cfg: dict) -> Path:
    plan, side, end = view_plan(cfg), view_side(cfg), view_end(cfg)
    left_w = plan.w
    right_w = max(side.w, end.w)
    gap = 44
    margin = 26
    header = 74
    notes = [
        "CHECKING MODEL, not a copy of the pedal: the envelope, the top-face plane, the four",
        "rubber pads, the five OEM head positions, and the treadle on its hinge. The jacks",
        "are not modelled - the plan knows which face they leave, not where along it, so the",
        "basket's windows are sized to clear any of the four positions rather than centred",
        "on measured holes.",
        "",
        "TREADLE: the rectified plan shows it raised and in parallax, so its outline is the",
        "weakest datum in this project. The mount is checked against the green sweep",
        "footprint, x -78.0 to +12.0, and against the plate's swing from -6 to +10 deg",
        "about the hinge - not merely against the treadle at rest.",
        "",
        "SCALE: from the owner's caliper stills, rectified onto the published 165.0 x 197.0.",
        "Nothing on this sheet is a manual dimension; the manual gives topology only.",
    ]
    notes_h = 16 + len(notes) * 18
    width = margin * 2 + left_w + gap + right_w
    height = header + plan.h + notes_h

    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.rectangle([6, 6, width - 7, height - 7], outline=INK, width=2)
    d.text((margin, 18), "DigiTech Whammy V  -  the device, as modelled", fill=INK,
           font=FONT_T)
    d.text((margin, 50), "External drawing used to check the mount.  1:1 at 4 px/mm.",
           fill=THIN, font=FONT)

    canvas.paste(plan.img, (margin, header))
    canvas.paste(side.img, (margin + left_w + gap, header))
    canvas.paste(end.img, (margin + left_w + gap, header + side.h + 8))

    d.text((margin + left_w // 2, header - 2), "PLAN  -  the device", fill=INK, font=FONT,
           anchor="ma")
    d.text((margin + left_w + gap + right_w // 2, header - 2),
           "SIDE ELEVATION  -  treadle at rest, and its travel", fill=INK, font=FONT,
           anchor="ma")
    d.text((margin + left_w + gap + right_w // 2, header + side.h + 6),
           "END ELEVATION  -  INPUT end", fill=INK, font=FONT, anchor="ma")

    y = header + plan.h + 12
    for line in notes:
        d.text((margin, y), line, fill=INK, font=FONT_S)
        y += 18

    REF.mkdir(parents=True, exist_ok=True)
    out = REF / "pedal_sheet.png"
    canvas.save(out)
    print("wrote", out.relative_to(PROJECT), canvas.size)
    return out


# --------------------------------------------------------------------------- #
# STL renders
# --------------------------------------------------------------------------- #


def read_stl(path: Path) -> np.ndarray:
    blob = path.read_bytes()
    count = struct.unpack_from("<I", blob, 80)[0]
    if 84 + 50 * count != len(blob):
        raise ValueError(f"{path.name} is not a binary STL")
    rec = np.frombuffer(blob, dtype=np.uint8, count=50 * count, offset=84).reshape(count, 50)
    return rec[:, 12:48].copy().view("<f4").reshape(count, 3, 3).astype(float)


def _view_matrix(elev_deg: float, azim_deg: float) -> np.ndarray:
    """Rotate model XYZ into a viewing frame where +z is depth toward the viewer."""
    e, a = np.radians(elev_deg), np.radians(azim_deg)
    rz = np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0, 0, 1]])
    rx = np.array([[1.0, 0.0, 0.0], [0.0, np.cos(e), -np.sin(e)],
                   [0.0, np.sin(e), np.cos(e)]])
    return rx @ rz


def render(layers, out: Path, title: str, elev=26.0, azim=-58.0,
           width=1180, height=900) -> Path:
    """Z-buffered orthographic render of one or more STLs, each with its own colour.

    matplotlib's Poly3DCollection sorts whole triangles by their average depth, which
    draws a cage over a pedal that is actually inside it. A z-buffer has no such
    problem, and it costs forty lines.
    """
    rot = _view_matrix(elev, azim)
    light_a = np.array([0.42, -0.52, 0.74])
    light_a /= np.linalg.norm(light_a)
    light_b = np.array([-0.55, -0.20, 0.60])
    light_b /= np.linalg.norm(light_b)

    tris, rgb = [], []
    for stl, base in layers:
        tri = read_stl(stl)
        tris.append(tri)
        rgb.append(np.tile(np.array(base, dtype=float), (len(tri), 1)))
    tri = np.concatenate(tris)
    base_rgb = np.concatenate(rgb)

    normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(normal, axis=1)
    length[length == 0] = 1.0
    normal /= length[:, None]
    shade = (np.clip(normal @ light_a, 0, 1) * 0.62
             + np.clip(normal @ light_b, 0, 1) * 0.22 + 0.20)
    shade = np.clip(shade, 0.0, 1.0)

    verts = tri.reshape(-1, 3) @ rot.T
    lo, hi = verts.min(0), verts.max(0)
    span = (hi - lo).max()
    centre = (lo + hi) / 2
    scale = 0.86 * min(width, height) / span
    px = (verts[:, 0] - centre[0]) * scale + width / 2
    py = height / 2 - (verts[:, 1] - centre[1]) * scale
    pz = verts[:, 2]

    image = np.ones((height, width, 3), dtype=float) * 1.0
    zbuf = np.full((height, width), -1e18)

    ptri = np.stack([px.reshape(-1, 3), py.reshape(-1, 3), pz.reshape(-1, 3)], axis=2)
    for i in range(len(tri)):
        t = ptri[i]
        x0 = max(int(np.floor(t[:, 0].min())), 0)
        x1 = min(int(np.ceil(t[:, 0].max())), width - 1)
        y0 = max(int(np.floor(t[:, 1].min())), 0)
        y1 = min(int(np.ceil(t[:, 1].max())), height - 1)
        if x1 < x0 or y1 < y0:
            continue
        ax, ay = t[0, 0], t[0, 1]
        bx, by = t[1, 0], t[1, 1]
        cx, cy = t[2, 0], t[2, 1]
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-9:
            continue
        xs = np.arange(x0, x1 + 1) + 0.5
        ys = np.arange(y0, y1 + 1) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / det
        w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / det
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        depth = w0 * t[0, 2] + w1 * t[1, 2] + w2 * t[2, 2]
        sub_z = zbuf[y0:y1 + 1, x0:x1 + 1]
        take = inside & (depth > sub_z)
        if not take.any():
            continue
        sub_z[take] = depth[take]
        image[y0:y1 + 1, x0:x1 + 1][take] = np.clip(base_rgb[i] * shade[i], 0, 1)

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    ax.imshow(image, interpolation="antialiased")
    ax.set_axis_off()
    ax.set_title(title, fontsize=12)
    fig.tight_layout(pad=0.4)
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    print("wrote", out.relative_to(PROJECT))
    return out


CAGE = (0.42, 0.62, 0.86)
PEDAL = (0.86, 0.62, 0.44)


def mount_sheet(cfg: dict) -> Path:
    spec = qm.load()
    plan, end = view_mount_plan(cfg, spec), view_mount_end(cfg, spec)
    margin, gap, header = 26, 50, 74
    notes = [
        "The mount: basket plus ring. Blue is the basket - floor, four 6.0 walls and ten R8",
        "stadium windows sized so any of the four plug positions clears. Green is the ring: a",
        "flat 3.7 plate whose lips reach inboard on all four sides to bear on the five OEM",
        "heads, and which pulls down on six countersunk M3. Red circles are those screws.",
        "",
        "Nothing reaches over the treadle: the ring's opening runs x -78.9 to +12.5, opened to",
        "+/-101.5 because a rocking plate swings its far corner outboard. That is checked by",
        "sweeping the treadle through its travel, not by eye.",
        "",
        "Clip rows 23 and 159 mm from the pedal's INPUT end - 136 apart, four board pitches -",
        "and the columns 76 apart, one board column. Both land on the board's rib grid.",
    ]
    width = margin * 2 + plan.w + gap + end.w
    height = header + plan.h + 16 + len(notes) * 18
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.rectangle([6, 6, width - 7, height - 7], outline=INK, width=2)
    d.text((margin, 18), "DigiTech Whammy V  -  the mount, as printed", fill=INK, font=FONT_T)
    d.text((margin, 50), "1:1 at 4 px/mm.  Basket and ring, with the pedal in outline.",
           fill=THIN, font=FONT)
    canvas.paste(plan.img, (margin, header))
    canvas.paste(end.img, (margin + plan.w + gap, header))
    d.text((margin + plan.w // 2, header - 2), "PLAN", fill=INK, font=FONT, anchor="ma")
    d.text((margin + plan.w + gap + end.w // 2, header - 2), "END ELEVATION", fill=INK,
           font=FONT, anchor="ma")
    y = header + plan.h + 12
    for line in notes:
        d.text((margin, y), line, fill=INK, font=FONT_S)
        y += 18
    out = REF / "mount_sheet.png"
    canvas.save(out)
    print("wrote", out.relative_to(PROJECT), canvas.size)
    return out


def main() -> int:
    cfg = load()
    device_sheet(cfg)
    mount_sheet(cfg)

    spec = qm.load()
    parts = qm.build(spec)
    qm.export(parts, ["base", "ring", "mount", "pedal", "fit"], "stl")

    stem = qm.STEM
    cage = DWG / f"{stem}.stl"
    pedal = DWG / f"{stem}_pedal.stl"
    DWG.mkdir(parents=True, exist_ok=True)

    render([(pedal, PEDAL)], DWG / "render_pedal.png",
           "Whammy V  -  the device (check model)")
    render([(cage, CAGE)], DWG / "render_cage.png",
           "QuickMount set  -  basket, ring, four clips")
    render([(pedal, PEDAL), (cage, CAGE)], DWG / "render_pedal_in_cage.png",
           "Whammy V seated in the cage  -  mount blue, pedal tan")
    render([(pedal, PEDAL), (cage, CAGE)], DWG / "render_pedal_in_cage_toe.png",
           "Seated, from the toe end", elev=10.0, azim=-118.0)
    render([(cage, CAGE)], DWG / "render_cage_top.png",
           "The set from above  -  the ring's opening is the treadle's space",
           elev=78.0, azim=-90.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
