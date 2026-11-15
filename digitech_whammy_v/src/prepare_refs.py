"""Clean, crop and rectify the owner's photo set for the DigiTech Whammy V.

The source images are phone stills of a pedal sitting on a table, with a digital
caliper laid open at 10.00 mm as a scale witness. They are usable as reference once
three things are undone: the camera roll, the perspective of a hand-held shot, and the
colour cast of the table.

Two of the seven stills are stored rotated. The EXIF orientation on this set is not
trustworthy as a whole - it says "rotate 90" on four files of which only two are
actually stored sideways - so the correction is a table here rather than an
``exif_transpose`` call, and the orientation of every file was settled by reading the
legends printed on the pedal ("INPUT", "POWER", "HARMONY") at full resolution.

What comes out, in ``ref/clean/``:

    <stamp>_clean.jpg         balanced, sharpened, cropped to the pedal plus a margin
    top_plan.png              the top face, squared up to the 165 x 197 footprint
    bottom_plan.png           the bottom face, same treatment
    *_plan_grid.png           the same with a 10 mm grid, for reading dimensions off

The plan views are rectified through a homography fitted to the four straight edges
of the pedal's silhouette, so the printed 165.0 x 197.0 footprint from the manual
fixes the scale of every feature inside it. That is the same rule the rest of the
repo follows: a photo may locate a feature, but a published dimension sets the size.

    .venv/Scripts/python digitech_whammy_v/src/prepare_refs.py
    .venv/Scripts/python digitech_whammy_v/src/prepare_refs.py --report
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

PROJECT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT / "ref" / "images_from_samsung_s24"
OUT_DIR = PROJECT / "ref" / "clean"

# Footprint the manual publishes (6.5 in x 7.75 in), used as the rectification target.
WIDTH_MM = 165.0
DEPTH_MM = 197.0
PLAN_PX_MM = 6.0

# name -> rotate 90 deg clockwise. See the module docstring: this table, not EXIF.
ORIENTATION = {
    "20261107_113055": True,  # top face, stored sideways
    "20261107_113135": True,  # bottom face, stored sideways
    "20261107_113201": False,
    "20261107_113237": False,
    "20261107_113321": False,
    "20261107_113338": False,
    "20261107_113408": False,
}

# Which of the stills is a square-on plan view, and of which face.
PLAN_VIEWS = {"20261107_113055": "top", "20261107_113135": "bottom"}


# --------------------------------------------------------------------------- #
# colour
# --------------------------------------------------------------------------- #


def _white_balance(im: Image.Image) -> Image.Image:
    """Grey-world on the table top, restricted to the bright neutral pixels.

    The pedal is saturated red and the slot field is near black, so neither survives
    the filter; what is left is the bench surface, which should be neutral.
    """
    a = np.asarray(im).astype(np.float32)
    flat = a.reshape(-1, 3)
    brightness = flat.mean(1)
    neutral = flat[(brightness > np.percentile(brightness, 60)) & (flat.max(1) - flat.min(1) < 24)]
    if len(neutral) < 500:
        return im
    target = float(neutral.mean())
    gains = target / np.maximum(neutral.mean(0), 1.0)
    gains = np.clip(gains, 0.85, 1.15)
    return Image.fromarray(np.clip(a * gains, 0, 255).astype(np.uint8))


def _tone(im: Image.Image) -> Image.Image:
    """Mild contrast with the ends left alone, so the reds do not clip."""
    lut = []
    for i in range(256):
        x = i / 255.0
        y = x + 0.22 * (x - 0.5) * (1.0 - abs(2.0 * x - 1.0))
        lut.append(round(max(0.0, min(1.0, y)) * 255))
    return im.point(lut * 3)


def _clean(im: Image.Image) -> Image.Image:
    im = _white_balance(im)
    im = _tone(im)
    return im.filter(ImageFilter.UnsharpMask(radius=2.0, percent=45, threshold=3))


# --------------------------------------------------------------------------- #
# silhouette
# --------------------------------------------------------------------------- #


def red_mask(im: Image.Image) -> np.ndarray:
    a = np.asarray(im).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mask = (r > 80) & (r - g > 40) & (r - b > 40)
    # The pedal is the one large red region; fill the label and the gaps inside it.
    filled = Image.fromarray((mask * 255).astype(np.uint8))
    filled = filled.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    filled = filled.filter(ImageFilter.MaxFilter(9))
    filled = filled.filter(ImageFilter.MinFilter(9))
    mask = np.asarray(filled) > 0
    keep = _largest_run(mask)
    return keep


def _largest_run(mask: np.ndarray) -> np.ndarray:
    """Keep only the mask rows/columns that belong to the pedal.

    A full connected-component pass is more than this needs: the only false red in
    these frames is a stray highlight, and the pedal spans the middle of the frame.
    """
    rows = mask.sum(1)
    cols = mask.sum(0)
    r_thr, c_thr = 0.15 * rows.max(), 0.15 * cols.max()
    r_lo = int(np.argmax(rows > r_thr))
    r_hi = int(len(rows) - np.argmax(rows[::-1] > r_thr))
    c_lo = int(np.argmax(cols > c_thr))
    c_hi = int(len(cols) - np.argmax(cols[::-1] > c_thr))
    out = np.zeros_like(mask)
    out[r_lo:r_hi, c_lo:c_hi] = mask[r_lo:r_hi, c_lo:c_hi]
    return out


def _robust_line(u: np.ndarray, v: np.ndarray) -> tuple[float, float]:
    """v = a*u + b, with two rounds of residual clipping."""
    keep = np.ones(u.shape, bool)
    a, b = 0.0, float(np.median(v))
    for _ in range(3):
        a, b = np.polyfit(u[keep], v[keep], 1)
        resid = v - (a * u + b)
        keep = np.abs(resid) < max(3.0, 3.0 * float(resid[keep].std()))
    return float(a), float(b)


def _hull(points: np.ndarray) -> np.ndarray:
    """Convex hull (monotone chain). The silhouette, without the black hardware in it.

    A moment fit over the red pixels is no good here: the treadle's black pad eats a
    third of the top face, which drags the principal axis round by 13 degrees. The hull
    is the shape of the object, so the longest hull edge is the long side.
    """
    pts = np.unique(points, axis=0)
    if len(pts) < 3:
        return pts

    def half(seq):
        out: list[tuple[float, float]] = []
        for p in seq:
            while len(out) >= 2:
                (ax, ay), (bx, by) = out[-2], out[-1]
                if (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) <= 0:
                    out.pop()
                else:
                    break
            out.append((float(p[0]), float(p[1])))
        return out

    lower = half(pts)
    upper = half(pts[::-1])
    return np.array(lower[:-1] + upper[:-1])


def outline(mask: np.ndarray) -> tuple[list[tuple[float, float]], float]:
    """Four straight sides of the rounded-rectangle silhouette, intersected.

    Fitted as lines rather than taken from the extreme silhouette pixels, because the
    R6.35 corners pull those pixels about 2 mm inboard of the true corner. The second
    return is the roll the part sits at in the frame: 0 is square to the image axes.
    """
    ys, xs = np.nonzero(mask)
    hull = _hull(np.stack([xs, ys], 1).astype(float)[::4])
    edges = np.roll(hull, -1, axis=0) - hull
    lengths = np.linalg.norm(edges, axis=1)
    longest = edges[int(np.argmax(lengths))]
    axis = math.atan2(longest[1], longest[0])
    # Roll relative to the nearest image axis, which is how the shot was framed.
    roll = math.degrees(axis) % 90.0
    roll = roll if roll <= 45.0 else roll - 90.0
    return _fit_rect(np.stack([xs, ys], 1).astype(float), math.atan2(longest[1], longest[0])), roll


def _fit_rect(pts: np.ndarray, theta: float) -> list[tuple[float, float]]:
    centre = pts.mean(0)
    ca, sa = math.cos(-theta), math.sin(-theta)
    rot = (pts - centre) @ np.array([[ca, -sa], [sa, ca]]).T
    u, v = rot[:, 0], rot[:, 1]
    u0, u1, v0, v1 = u.min(), u.max(), v.min(), v.max()

    band = 20.0
    mid_u = (u > u0 + 0.1 * (u1 - u0)) & (u < u1 - 0.1 * (u1 - u0))
    mid_v = (v > v0 + 0.1 * (v1 - v0)) & (v < v1 - 0.1 * (v1 - v0))
    faces = {
        "top": (v <= v0 + band) & mid_u,
        "bottom": (v >= v1 - band) & mid_u,
        "left": (u <= u0 + band) & mid_v,
        "right": (u >= u1 - band) & mid_v,
    }
    fits = {}
    for key, sel in faces.items():
        if key in ("top", "bottom"):
            fits[key] = _robust_line(u[sel], v[sel])
        else:
            fits[key] = _robust_line(v[sel], u[sel])

    def meet(horiz: str, vert: str) -> tuple[float, float]:
        a_v, b_v = fits[horiz]
        a_u, b_u = fits[vert]
        uu = (a_u * b_v + b_u) / (1.0 - a_u * a_v)
        return uu, a_v * uu + b_v

    corners_rot = [meet("top", "left"), meet("top", "right"),
                   meet("bottom", "right"), meet("bottom", "left")]
    back = np.array([[ca, -sa], [sa, ca]]).T
    return [tuple((np.asarray(p) @ back + centre).tolist()) for p in corners_rot]


def homography(src: list, dst: list) -> np.ndarray:
    rows = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(rows, float))
    return vt[-1].reshape(3, 3)


def rectify(im: Image.Image, corners: list, px_mm: float = PLAN_PX_MM) -> Image.Image:
    """Warp the silhouette onto the published footprint, at a fixed px/mm."""
    pts = [np.asarray(p, float) for p in corners]
    lengths = [float(np.linalg.norm(pts[(i + 1) % 4] - pts[i])) for i in range(4)]
    ordered = pts if (lengths[0] + lengths[2]) < (lengths[1] + lengths[3]) else \
        [pts[1], pts[2], pts[3], pts[0]]
    dst = [(0.0, 0.0), (WIDTH_MM, 0.0), (WIDTH_MM, DEPTH_MM), (0.0, DEPTH_MM)]
    h = homography(ordered, dst)
    scale = np.array([[px_mm, 0, 0], [0, px_mm, 0], [0, 0, 1.0]])
    inverse = np.linalg.inv(scale @ h)
    inverse /= inverse[2, 2]
    return im.transform(
        (round(WIDTH_MM * px_mm), round(DEPTH_MM * px_mm)),
        Image.PERSPECTIVE,
        tuple(inverse.ravel()[:8]),
        resample=Image.BICUBIC,
    )


# --------------------------------------------------------------------------- #
# feature read-out
# --------------------------------------------------------------------------- #


def _blobs(mask: np.ndarray, min_px: int):
    """Connected components of a boolean mask, via a two-pass label in numpy."""
    try:
        from scipy import ndimage as ndi
    except ImportError:  # pragma: no cover - optional tooling
        return []
    lab, _ = ndi.label(mask)
    out = []
    for index, sl in enumerate(ndi.find_objects(lab), start=1):
        if sl is None:
            continue
        ys, xs = sl
        area = int((lab[sl] == index).sum())
        if area < min_px:
            continue
        out.append(
            {
                "area_px": area,
                "cx_px": (xs.start + xs.stop) / 2.0,
                "cy_px": (ys.start + ys.stop) / 2.0,
                "w_px": xs.stop - xs.start,
                "h_px": ys.stop - ys.start,
            }
        )
    return out


def read_plan(im: Image.Image, px_mm: float = PLAN_PX_MM) -> dict:
    """Dark round features on a rectified plan view, in millimetres.

    Coordinates are ``x_from_panel_edge`` and ``y_from_input_end``: on the top view the
    button strip is the x = 0 side and the INPUT/MIDI end is the y = 0 end, which the
    footswitch, the red LED and the treadle hinge all sit at. The blueprint maps those
    two axes onto the project frame.
    """
    a = np.asarray(im).astype(np.int16)
    dark = (a[..., 0] < 110) & (a[..., 1] < 110) & (a[..., 2] < 110)
    found = []
    for blob in _blobs(dark, int(px_mm * px_mm * 20)):
        w, h = blob["w_px"] / px_mm, blob["h_px"] / px_mm
        dia = (w + h) / 2.0
        if not (3.5 <= dia <= 20.0) or max(w, h) / min(w, h) > 1.25:
            continue
        x, y = blob["cx_px"] / px_mm, blob["cy_px"] / px_mm
        # A blob on the frame border is a cut-off feature, not a hole.
        if min(x, y, WIDTH_MM - x, DEPTH_MM - y) < 0.2 * dia:
            continue
        found.append(
            {
                "x_from_panel_edge": round(x, 2),
                "y_from_input_end": round(y, 2),
                "dia_mm": round(dia, 2),
            }
        )
    return {
        "features": sorted(found, key=lambda f: (f["y_from_input_end"], f["x_from_panel_edge"]))
    }


def annotate(im: Image.Image, px_mm: float, title: str) -> Image.Image:
    out = im.copy()
    draw = ImageDraw.Draw(out)
    step = 10.0
    for k in range(0, int(WIDTH_MM) + 1, int(step)):
        x = k * px_mm
        draw.line([(x, 0), (x, out.height)], fill=(0, 220, 255), width=1)
        draw.text((x + 2, out.height - 14), str(k), fill=(255, 255, 0))
    for k in range(0, int(DEPTH_MM) + 1, int(step)):
        y = k * px_mm
        draw.line([(0, y), (out.width, y)], fill=(0, 220, 255), width=1)
        draw.text((2, y + 1), str(k), fill=(255, 255, 0))
    draw.text((6, 6), f"{title}  {WIDTH_MM:g} x {DEPTH_MM:g} mm, grid 10 mm", fill=(255, 255, 0))
    return out


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #


def load(name: str) -> Image.Image:
    im = Image.open(SRC_DIR / f"{name}.jpg").convert("RGB")
    if ORIENTATION[name]:
        im = ImageOps.exif_transpose(im)
    return im


def crop_to_subject(im: Image.Image, margin: float = 0.04) -> Image.Image:
    mask = red_mask(im)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return im
    mx = int(margin * (xs.max() - xs.min()))
    my = int(margin * (ys.max() - ys.min()))
    return im.crop(
        (
            max(0, xs.min() - mx),
            max(0, ys.min() - my),
            min(im.width, xs.max() + mx),
            min(im.height, ys.max() + my),
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--report", action="store_true", help="print the read-out only")
    parser.add_argument("--max-px", type=int, default=2200, help="long edge of a cleaned still")
    args = parser.parse_args(argv)

    if not SRC_DIR.exists():
        raise SystemExit(f"source stills are missing: {SRC_DIR}")

    report: dict[str, dict] = {}
    args.out.mkdir(parents=True, exist_ok=True)

    for path in sorted(SRC_DIR.glob("*.jpg")):
        name = path.stem
        if name not in ORIENTATION:
            print(f"  skip {name}: not in the orientation table", file=sys.stderr)
            continue
        im = load(name)
        mask = red_mask(im)
        corners, roll = outline(mask)
        entry = {"roll_deg": round(roll, 2)}

        if name in PLAN_VIEWS:
            face = PLAN_VIEWS[name]
            clean = rectify(_clean(im), corners)
            if not args.report:
                clean.save(args.out / f"{face}_plan.jpg", quality=92, subsampling=1)
                annotate(clean, PLAN_PX_MM, f"{face} face").save(
                    args.out / f"{face}_plan_grid.jpg", quality=92, subsampling=1
                )
            entry.update(read_plan(clean))
            entry["face"] = face
        else:
            clean = crop_to_subject(_clean(im))
            long_edge = max(clean.size)
            if long_edge > args.max_px:
                k = args.max_px / long_edge
                clean = clean.resize(
                    (int(clean.width * k), int(clean.height * k)), Image.LANCZOS
                )
            if not args.report:
                clean.save(args.out / f"{name}_clean.jpg", quality=90, subsampling=1)
        report[name] = entry
        print(f"  {name}  roll {roll:+.2f} deg  " + ("plan" if name in PLAN_VIEWS else "elevation"))

    if not args.report:
        (args.out / "readout.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
