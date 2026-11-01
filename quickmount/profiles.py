"""2D profile helpers (shapely -> point lists for build123d)."""

from __future__ import annotations

from shapely.geometry import LineString


def stroke_polygon(points, thickness: float, resolution: int = 24):
    """Thicken a polyline into a closed polygon of constant width.

    Round joins keep the flexure smooth; square caps are avoided so the profile
    never overshoots a designed face by half a wall thickness at the ends.
    """
    line = LineString(points)
    return line.buffer(
        thickness / 2.0,
        cap_style="flat",
        join_style="round",
        resolution=resolution,
    )
