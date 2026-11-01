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
    z < 0        below the bar: post, arch, skirt
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

    @property
    def post_t(self) -> float:
        return self.post_outer - self.post_inner

    def summary(self) -> dict:
        return {
            "width_mm": round(self.width, 2),
            "ring_reach_mm": round(abs(self.ring_outer_x), 2),
            "ring_depth_mm": round(self.ring_depth, 2),
            "post_thickness_mm": round(self.post_t, 2),
            "bar_thickness_mm": round(self.bar_t, 2),
            "arch_span_mm": round(self.arch_span, 2),
        }


def load_spec(path: pathlib.Path = CLIP_YAML) -> KeeperSpec:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    pts = [(float(x), float(z)) for x, z in raw["profile_xz"]]
    bar_z = float(raw["bar_underside_z"])
    xs = [p[0] for p in pts]

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
    )


def _ring_polygon(spec: KeeperSpec, overlap: float = 1.5) -> SPoly:
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
    return SPoly([(x - spec.post_inner, z - spec.bar_z) for x, z in ring.exterior.coords])


def build_ring(spec: KeeperSpec | None = None, mirror: bool = False):
    """One keeper ring, inner face at x = 0, bar underside at z = 0."""
    s = spec or load_spec()
    pts = list(_ring_polygon(s).exterior.coords)[:-1]
    if mirror:
        pts = [(-x, z) for x, z in pts]
    solid = extrude(Plane.XZ * Polygon(*pts, align=None), amount=s.width)
    bb = solid.bounding_box()
    return Pos(0, -(bb.min.Y + bb.max.Y) / 2, 0) * solid


def build_arrangement(spec: KeeperSpec | None = None, rings: int = 2, pitch: float | None = None):
    """A bar with `rings` keeper rings: one at each end plus any in between.

    Ring spacing is `pitch` (default: the measured reference spacing). The bar
    length follows from it, so the bar ends land on the post faces.
    """
    s = spec or load_spec()
    p = pitch if pitch is not None else 32.90
    if rings < 1:
        raise ValueError("need at least one ring")

    # Ring centres sit half a post inboard of the bar ends.
    post_offset = s.post_t / 2.0
    bar_len = p * (rings - 1) + 2.0 * post_offset
    part = extrude(
        Plane.XY * Polygon(
            (-bar_len / 2, -s.width / 2),
            (bar_len / 2, -s.width / 2),
            (bar_len / 2, s.width / 2),
            (-bar_len / 2, s.width / 2),
            align=None,
        ),
        amount=s.bar_t,
    )

    centres = [-(rings - 1) * p / 2.0 + i * p for i in range(rings)]
    for c in centres:
        mirrored = c > 0
        ring = build_ring(s, mirror=mirrored)
        x = c + post_offset if mirrored else c - post_offset
        part = part + Pos(x, 0, 0) * ring
    return part, bar_len


def export(part, stl_path: str, step_path: str | None = None) -> None:
    export_stl(part, stl_path, tolerance=0.02, angular_tolerance=0.2)
    if step_path:
        export_step(part, step_path)
