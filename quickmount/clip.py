"""The slot clip, taken from the measured reference cross-section.

The clip is a constant cross-section extruded across its width. One section
contains two hooks joined by a flat bar:

    arch  __        __  arch
         /  \\      /  \\
   skirt|    |    |    |skirt
        |    |    |    |
        |    ||    ||    |
        +----+------+----+   <- bar
                |

`catalog/clips/reference_2space_clip.yaml` holds the measured polygon. The
measured bar is 3.00 mm thick, which is exactly the plate thickness, so when the
clip is merged into a baseplate the bar becomes part of the plate and only the
hooks protrude below it.

Two mount modes are provided because the reference part is ambiguous about which
face clamps the sheet; see docs/quickmount-mechanism.md section 6.

  bar_on_sheet     plate/bar underside on the sheet, hooks hang below
  bar_under_sheet  bar underside against the sheet underside, hooks rise above
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

import yaml
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIP_YAML = ROOT / "catalog" / "clips" / "reference_2space_clip.yaml"


@dataclass(frozen=True)
class ClipProfile:
    points: tuple[tuple[float, float], ...]
    width: float
    bar_z: float
    centre_x: float

    @property
    def span_x(self) -> tuple[float, float]:
        xs = [p[0] for p in self.points]
        return min(xs) - self.centre_x, max(xs) - self.centre_x

    @property
    def hook_centres_x(self) -> tuple[float, float]:
        """Post centre lines, measured at the bar ends."""
        return (-16.45, 16.45)

    @property
    def depth_below_bar(self) -> float:
        """Distance from the bar underside to the lowest point of the arch."""
        return max(p[1] for p in self.points) - self.bar_z

    @property
    def skirt_tip_below_bar(self) -> float:
        return self.bar_z - min(p[1] for p in self.points)


def load_profile(path: pathlib.Path = CLIP_YAML) -> ClipProfile:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    pts = tuple((float(x), float(z)) for x, z in raw["profile_xz"])
    xs = [p[0] for p in pts]
    return ClipProfile(
        points=pts,
        width=float(raw["extrude_y_mm"]),
        bar_z=float(raw["bar_underside_z"]),
        centre_x=(min(xs) + max(xs)) / 2.0,
    )


def _section_solid(pts, width: float):
    """Extrude a closed (x, z) polygon across `width` in Y, centred on y = 0."""
    solid = extrude(Plane.XZ * Polygon(*pts, align=None), amount=width)
    bb = solid.bounding_box()
    return Pos(0, -(bb.min.Y + bb.max.Y) / 2, 0) * solid


def build_reference_clip(profile: ClipProfile | None = None):
    """The clip exactly as measured, in its own coordinates."""
    p = profile or load_profile()
    return _section_solid(p.points, p.width)


def hook_section(profile: ClipProfile, x_sign: float = 1.0, bar_at_zero: bool = True):
    """Return the clip section re-based so the bar underside is at z = 0.

    `x_sign` of -1 mirrors the section so a single hook can be placed on the far
    side of a plate.
    """
    pts = []
    for x, z in profile.points:
        u = (x - profile.centre_x) * x_sign
        w = -(z - profile.bar_z) if bar_at_zero else z
        pts.append((u, w))
    return pts


def build_plate_with_clip(
    plate_w: float,
    plate_d: float,
    t_plate: float,
    screw_xy,
    screw_head_od: float,
    hole_d: float = 3.8,
    csk_extra: float = 0.2,
    corner_r: float = 3.0,
    hook_stations_y: tuple[float, ...] = (),
    mount_mode: str = "bar_on_sheet",
    clip: ClipProfile | None = None,
    pitch_mm: float | None = None,
):
    """A pedal baseplate carrying the reference hook geometry.

    The clip's bar is 3.00 mm thick, the same as the plate, so the bar is absorbed
    by the plate and only the hooks remain visible below (or above) it.

    `pitch_mm` rescales the section across X so the two hook centre lines land
    exactly one slot pitch apart, which is what the reference part assumes.
    """
    p = clip or load_profile()
    flip = mount_mode == "bar_under_sheet"

    part = extrude(RectangleRounded(plate_w, plate_d, corner_r), amount=t_plate)

    sx = 1.0
    if pitch_mm is not None:
        sx = (pitch_mm / 2.0) / p.hook_centres_x[1]

    section = hook_section(p, 1.0, bar_at_zero=True)
    section = [(x * sx, z) for x, z in section]
    if flip:
        section = [(x, -z) for x, z in section]
    section = [(x, z + (t_plate - 3.0)) for x, z in section]

    hook = _section_solid(section, p.width)
    for y in hook_stations_y:
        part = part + Pos(0, y, 0) * hook

    hole_r = hole_d / 2.0
    csk_r = screw_head_od / 2.0 + csk_extra
    csk_depth = csk_r - hole_r
    for x, y in screw_xy:
        part = part - Pos(x, y, t_plate / 2) * Cylinder(hole_r, t_plate + 2)
        part = part - Pos(x, y, csk_depth / 2) * Cone(csk_r, hole_r, csk_depth)

    try:
        bottom = part.edges().filter_by(lambda e: abs(e.center().Z) < 1e-6)
        if bottom:
            part = chamfer(bottom, 0.4)
    except Exception:
        pass

    return part


def export(part, stl_path: str, step_path: str | None = None) -> None:
    export_stl(part, stl_path, tolerance=0.02, angular_tolerance=0.2)
    if step_path:
        export_step(part, step_path)
