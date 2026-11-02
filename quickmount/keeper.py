"""C-shaped keeper rings and their arrangements.

A keeper ring is the loop that engages the RockBoard slot grid: a post that drops
through a slot, an arch that springs over the neighbouring rib, and a thin skirt
that comes back down. The reference part carries two rings on a 3 mm bar; a drawn
out version of one ring is the unit this module builds.

Geometry comes from the measured cross-section in
`catalog/clips/reference_2space_clip.yaml`, so every dimension is traceable to a
sliced mesh rather than to guesswork.

Coordinates (use frame, one ring):
    x = 0        inner face of the post, where it meets the bar
    x < 0        outward: arch reach and skirt
    z = 0        bar/plate underside
    z > 0        above the plate: post, arch, skirt rise to z = +19.64

The pedal side of the plate is therefore z = 0 and the board side is z = bar_t,
which is the face the countersinks open on.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

import yaml
from build123d import (
    Plane,
    Polygon,
    Pos,
    extrude,
    export_step,
    export_stl,
)
from shapely.geometry import Polygon as SPoly
from shapely.geometry import box

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIP_YAML = ROOT / "catalog" / "clips" / "reference_2space_clip.yaml"


@dataclass(frozen=True)
class KeeperSpec:
    """Measured geometry of one keeper ring."""

    points: tuple[tuple[float, float], ...]
    bar_z: float          # bar underside in the file's axis
    width: float          # extrusion width across the ring
    post_inner: float     # x of the post face that meets the bar
    post_outer: float
    ring_inner_x: float   # after re-basing: inner face at 0, so 0.0
    ring_outer_x: float   # most outboard point (negative)
    ring_depth: float     # below the bar underside, positive
    bar_t: float          # bar thickness == plate thickness
    arch_span: float = 16.8   # post outer face to skirt inner face (clears the rib)
    arch_base_depth: float = 10.0  # arch base below the bar underside

    @property
    def post_t(self) -> float:
        return abs(self.post_outer - self.post_inner)

    @property
    def arch_pivot(self) -> float:
        """Local x of the post's outer face, the point the arch springs from."""
        return self.post_outer - self.post_inner

    def scaled_arch_span(self, arch_scale: float) -> float:
        return self.arch_span * arch_scale

    def summary(self) -> dict:
        return {
            "width_mm": round(self.width, 2),
            "ring_reach_mm": round(abs(self.ring_outer_x), 2),
            "ring_depth_mm": round(self.ring_depth, 2),
            "post_thickness_mm": round(self.post_t, 2),
            "bar_thickness_mm": round(self.bar_t, 2),
            "arch_span_mm": round(self.arch_span, 2),
            "arch_base_depth_mm": round(self.arch_base_depth, 2),
        }


def load_spec(path: pathlib.Path = CLIP_YAML) -> KeeperSpec:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    pts = [(float(x), float(z)) for x, z in raw["profile_xz"]]
    bar_z = float(raw["bar_underside_z"])
    xs = [p[0] for p in pts]

    if "post_inner_x" in raw and "post_outer_x" in raw:
        # a clip-only profile, with no bar to derive the post faces from
        post_inner = float(raw["post_inner_x"])
        post_outer = float(raw["post_outer_x"])
    else:
        # The bar's ends are long vertical edges. Find them rather than assuming.
        verticals = []
        for (x0, z0), (x1, z1) in zip(pts, pts[1:] + pts[:1]):
            if abs(x0 - x1) < 1e-6 and abs(z1 - z0) > 5.0:
                verticals.append((round(x0, 2), abs(z1 - z0)))
        verticals = sorted(set(verticals))
        right = [v for v in verticals if v[0] > 0]
        if len(right) < 2:
            raise ValueError(f"cannot locate the bar ends in {path}")
        post_inner, post_outer = right[0][0], right[1][0]

    return KeeperSpec(
        points=tuple(pts),
        bar_z=bar_z,
        width=float(raw["extrude_y_mm"]),
        post_inner=post_inner,
        post_outer=post_outer,
        ring_inner_x=0.0,
        ring_outer_x=min(xs) - post_outer,
        ring_depth=max(z for _, z in pts) - bar_z,
        bar_t=3.0,
        arch_span=float(raw.get("arch_span_mm", 16.8)),
        arch_base_depth=float(raw.get("arch_base_depth_mm", 10.0)),
    )


def _ring_polygon(spec: KeeperSpec, overlap: float = 1.5, arch_scale: float = 1.0) -> SPoly:
    """One ring, re-based so the bar end lies at x = 0 and the bar underside at z = 0.

    The cut runs `overlap` inboard of the bar end, so the ring carries a sliver of
    bar and fuses to an arrangement bar instead of butting against it.
    """
    poly = SPoly(spec.points).buffer(0)
    face = spec.post_inner + overlap
    cut = box(face - 100.0, spec.bar_z - 100.0, face, spec.bar_z + 100.0)
    ring = poly.intersection(cut)
    if ring.is_empty:
        raise ValueError("ring cut produced an empty polygon")
    pivot = spec.post_outer - spec.post_inner
    pts = []
    for x, z in ring.exterior.coords:
        u = x - spec.post_inner
        # stretch only the part outboard of the post face, so the post keeps its
        # thickness and only the arch reach changes
        if u < pivot:
            u = pivot + (u - pivot) * arch_scale
        pts.append((u, z - spec.bar_z))
    return SPoly(pts)


def build_ring(
    spec: KeeperSpec | None = None,
    mirror: bool = False,
    arch_scale: float = 1.0,
    width: float | None = None,
):
    """One keeper ring, inner face at x = 0, bar underside at z = 0.

    `width` is the across-slot dimension. Retention is spring pressure of the thin
    skirt against the slot edge, so this must be close to the slot width - being
    narrower than the slot means no contact and no pressure.
    """
    s = spec or load_spec()
    w = s.width if width is None else width
    pts = list(_ring_polygon(s, arch_scale=arch_scale).exterior.coords)[:-1]
    if mirror:
        pts = [(-x, z) for x, z in pts]
    solid = extrude(Plane.XZ * Polygon(*pts, align=None), amount=w)
    bb = solid.bounding_box()
    return Pos(0, -(bb.min.Y + bb.max.Y) / 2, 0) * solid


def build_arrangement(
    spec: KeeperSpec | None = None,
    rings: int = 2,
    pitch: float | None = None,
    arch_scale: float = 1.0,
    width: float | None = None,
):
    """A bar with `rings` keeper rings: one at each end plus any in between.

    Ring spacing is `pitch` (default: the measured reference spacing). The bar
    length follows from it, so the bar ends land on the post faces.
    """
    s = spec or load_spec()
    w = s.width if width is None else width
    p = pitch if pitch is not None else 32.90
    if rings < 1:
        raise ValueError("need at least one ring")

    # Ring centres sit half a post inboard of the bar ends.
    post_offset = s.post_t / 2.0
    bar_len = p * (rings - 1) + 2.0 * post_offset
    part = extrude(
        Plane.XY * Polygon(
            (-bar_len / 2, -w / 2),
            (bar_len / 2, -w / 2),
            (bar_len / 2, w / 2),
            (-bar_len / 2, w / 2),
            align=None,
        ),
        amount=s.bar_t,
    )

    centres = [-(rings - 1) * p / 2.0 + i * p for i in range(rings)]
    for c in centres:
        mirrored = c > 0
        ring = build_ring(s, mirror=mirrored, arch_scale=arch_scale, width=w)
        x = c + post_offset if mirrored else c - post_offset
        part = part + Pos(x, 0, 0) * ring
    return part, bar_len


def export(part, stl_path: str, step_path: str | None = None) -> None:
    export_stl(part, stl_path, tolerance=0.02, angular_tolerance=0.2)
    if step_path:
        export_step(part, step_path)
