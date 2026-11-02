"""Component model for a QuickMount-compatible pedal mount.

Two attachment problems are kept apart:

    board attachment   ->  spine(s): clips strung along an axis, plus the plate
                           clearance each clip needs to flex outward
    pedal attachment   ->  wing(s): plate or beam surfaces reaching the pedal's
                           mount holes, or vertical retainer columns, or both

A spine is not a special case of a plate; it is an axial arrangement of clips.
The reference 125B part is one spine of two clips running across the board slots,
with two wings running out to the four corner screw holes.

Coordinates follow `keeper.py`: the plate lies in XY with its pedal face at z = 0,
and clips rise above z = 0 on the board side. The OEM mesh has the same part
rotated, plate in XZ and clips reaching +Y.
"""

from __future__ import annotations

from dataclasses import dataclass

from build123d import (
    Align,
    Box,
    Compound,
    Cone,
    Cylinder,
    Face,
    Plane,
    Polygon,
    Pos,
    Rectangle,
    RectangleRounded,
    Rot,
    Text,
    Wire,
    extrude,
)

from .keeper import KeeperSpec, build_ring, load_spec
from shapely.geometry import Polygon as ShapelyPolygon

BOTTOM = (Align.CENTER, Align.CENTER, Align.MIN)
DIRECTIONS = {"-x": (-1.0, 0.0), "+x": (1.0, 0.0), "-y": (0.0, -1.0), "+y": (0.0, 1.0)}


@dataclass(frozen=True)
class SpineSpec:
    """Clips strung along one axis: the board attachment.

    `post_spacing` is the distance between clip post faces and must equal the
    board's slot pitch. `axis` is the direction the clips are spaced along, which
    is also the direction the arches flare: across the slots for a two-row mount,
    along them for a single-row one. `flare` is "outward" for a spine that spans
    two rows (clips flare away from the centre) or "inline" for one row (all
    clips flare the same way, like the reference 2-space clip).
    """

    clips: int = 2
    post_spacing: float = 76.2
    axis: str = "x"
    clip_width: float = 17.4       # across the slot
    arch_scale: float = 1.0
    clearance: float = 2.0         # plate cut beyond each arch
    clearance_width: float = 0.0   # extra notch width across the clip
    clearance_radius: float = 0.0  # rounded inner corners of the notch
    flare: str = "outward"         # "outward" or "inline"
    offset: float = 0.0            # spine centre along the other axis
    name: str = "spine"


@dataclass(frozen=True)
class MountHole:
    """A pedal baseplate screw hole, in plate coordinates."""

    x: float
    y: float
    bore: float = 3.7
    csk_dia: float = 6.7
    csk_face: str = "bottom"       # the countersink opens on this face

    @property
    def csk_depth(self) -> float:
        return (self.csk_dia - self.bore) / 2.0


@dataclass(frozen=True)
class BrandStamp:
    """Recessed branding with rounded frames on the flat pedal-facing surface."""

    model_number: str
    x: float = 0.0
    y: float = 0.0
    font: str = "Arial"
    font_path: str | None = None
    font_size: float = 5.0
    bold_amount: float = 0.0
    line_spacing: float = 6.0
    model_gap: float = 10.0
    depth: float = 0.4
    frame_padding: float = 1.2
    frame_width: float = 0.8
    frame_radius: float = 2.0
    rotation: float = 90.0


@dataclass(frozen=True)
class RetainerColumn:
    """A vertical post that catches the side of a pedal with no baseplate holes."""

    x: float
    y: float
    height: float = 10.0
    thickness: float = 2.5
    depth: float = 12.0
    facing: str = "-x"             # the side the pedal sits on
    lip: float = 1.2
    name: str = "column"


@dataclass(frozen=True)
class Pocket:
    """A clearance cut in a wing: battery door, rubber-foot pocket, label relief."""

    cx: float
    cy: float
    width: float
    depth: float
    corner_radius: float = 0.0
    through: bool = True
    depth_mm: float = 0.0          # used when `through` is False
    name: str = "pocket"


@dataclass(frozen=True)
class WingSpec:
    """A plate or beam: the pedal attachment."""

    name: str
    outline: tuple[tuple[float, float], ...] = ()
    width_mm: float = 0.0
    depth_mm: float = 0.0
    corner_radius: float = 0.0
    cx: float = 0.0
    cy: float = 0.0
    holes: tuple[MountHole, ...] = ()
    columns: tuple[RetainerColumn, ...] = ()
    pockets: tuple[Pocket, ...] = ()

    def points(self) -> tuple[tuple[float, float], ...]:
        if self.outline:
            return self.outline
        hw, hd = self.width_mm / 2.0, self.depth_mm / 2.0
        return (
            (self.cx - hw, self.cy - hd),
            (self.cx + hw, self.cy - hd),
            (self.cx + hw, self.cy + hd),
            (self.cx - hw, self.cy + hd),
        )


@dataclass(frozen=True)
class MountSpec:
    """A whole mount: spines for the board, wings for the pedal."""

    name: str
    thickness: float = 3.0
    spines: tuple[SpineSpec, ...] = ()
    wings: tuple[WingSpec, ...] = ()
    holes: tuple[MountHole, ...] = ()
    columns: tuple[RetainerColumn, ...] = ()
    brand_stamp: BrandStamp | None = None


def _plate(wing: WingSpec, thickness: float):
    if wing.corner_radius > 0 and not wing.outline:
        sketch = Pos(wing.cx, wing.cy, 0) * RectangleRounded(
            wing.width_mm, wing.depth_mm, wing.corner_radius
        )
    else:
        sketch = Plane.XY * Polygon(*wing.points(), align=None)
    return extrude(sketch, amount=thickness)


def _pocket_cutter(pocket: Pocket, thickness: float):
    height = thickness + 2.0 if pocket.through else pocket.depth_mm
    if pocket.corner_radius > 0:
        sketch = Pos(pocket.cx, pocket.cy, 0) * RectangleRounded(
            pocket.width, pocket.depth, pocket.corner_radius
        )
    else:
        sketch = Pos(pocket.cx, pocket.cy, 0) * Rectangle(pocket.width, pocket.depth)
    solid = extrude(sketch, amount=height)
    z0 = -1.0 if pocket.through else thickness - pocket.depth_mm
    return Pos(0, 0, z0) * solid


def _csk_cutter(hole: MountHole, thickness: float):
    """Through bore plus a 90 degree countersink on the requested face."""
    r_bore, r_face = hole.bore / 2.0, hole.csk_dia / 2.0
    depth = hole.csk_depth
    if hole.csk_face == "bottom":
        cone = Pos(hole.x, hole.y, 0) * Cone(r_face, r_bore, depth, align=BOTTOM)
    else:
        cone = Pos(hole.x, hole.y, thickness - depth) * Cone(r_bore, r_face, depth, align=BOTTOM)
    bore = Pos(hole.x, hole.y, -1.0) * Cylinder(hole.bore / 2.0, thickness + 2.0, align=BOTTOM)
    return cone + bore


def _bold_text_outline(outline, amount: float):
    """Expand each text face in 2D to synthesize bold weight from a regular font."""
    if amount == 0:
        return outline

    bold_faces = []
    for face in outline.faces():
        def points(wire: Wire):
            return [(vertex.center().X, vertex.center().Y) for vertex in wire.vertices()]

        glyph = ShapelyPolygon(
            points(face.outer_wire()),
            [points(wire) for wire in face.inner_wires()],
        )
        if not glyph.is_valid:
            glyph = glyph.buffer(0)
        expanded = glyph.buffer(amount, quad_segs=8, join_style="round")
        polygons = (
            [expanded]
            if isinstance(expanded, ShapelyPolygon)
            else [shape for shape in expanded.geoms if isinstance(shape, ShapelyPolygon)]
        )
        if not polygons:
            raise ValueError("bold expansion produced no closed text outlines")

        for polygon in polygons:
            outer = Wire.make_polygon(
                [(x, y, 0) for x, y in list(polygon.exterior.coords)[:-1]]
            )
            inner = [
                Wire.make_polygon([(x, y, 0) for x, y in list(ring.coords)[:-1]])
                for ring in polygon.interiors
            ]
            bold_faces.append(Face(outer, inner_wires=inner))
    return Compound(bold_faces)


def _brand_frame_cutter(text_cutters, stamp: BrandStamp):
    """Create a rounded recessed frame around the bounds of one or more text lines."""
    bounds = [cutter.bounding_box() for cutter in text_cutters]
    x_min = min(bound.min.X for bound in bounds) - stamp.frame_padding
    x_max = max(bound.max.X for bound in bounds) + stamp.frame_padding
    y_min = min(bound.min.Y for bound in bounds) - stamp.frame_padding
    y_max = max(bound.max.Y for bound in bounds) + stamp.frame_padding
    width, height = x_max - x_min, y_max - y_min
    if min(width, height) <= 2.0 * stamp.frame_width:
        raise ValueError("brand stamp frame width is too large for its text bounds")

    radius = min(stamp.frame_radius, width / 2.0, height / 2.0)
    inner_radius = max(0.0, radius - stamp.frame_width)
    cx, cy = (x_min + x_max) / 2.0, (y_min + y_max) / 2.0
    outer = Pos(cx, cy) * RectangleRounded(width, height, radius)
    inner = Pos(cx, cy) * RectangleRounded(
        width - 2.0 * stamp.frame_width,
        height - 2.0 * stamp.frame_width,
        inner_radius,
    )
    frame = extrude(
        outer - inner,
        amount=stamp.depth + 0.01,
        dir=(0, 0, 1),
    )
    return Pos(0, 0, -0.01) * frame


def _brand_stamp_cutters(stamp: BrandStamp):
    """Make centered cutters for the two company lines and spaced model line."""
    if not stamp.model_number.strip():
        raise ValueError("brand stamp model number cannot be empty")
    if (
        stamp.font_size <= 0
        or stamp.line_spacing <= 0
        or stamp.depth <= 0
        or stamp.model_gap < 0
        or stamp.bold_amount < 0
        or stamp.frame_padding < 0
        or stamp.frame_width < 0
        or stamp.frame_radius < 0
    ):
        raise ValueError(
            "brand stamp sizes and depth must be positive; frame, bold, and model-gap values cannot be negative"
        )
    if stamp.frame_width > 0 and stamp.frame_padding <= stamp.frame_width:
        raise ValueError("brand stamp frame padding must exceed its stroke width")

    model_offset = stamp.line_spacing + stamp.model_gap / 2.0
    text_cutters = []
    for text, line_offset in (
        ("Melting", model_offset),
        ("Skies", stamp.model_gap / 2.0),
        (stamp.model_number, -model_offset),
    ):
        if stamp.font_path is None:
            outline = Text(text, font_size=stamp.font_size, font=stamp.font, align=Align.CENTER)
        else:
            outline = Text(
                text,
                font_size=stamp.font_size,
                font_path=stamp.font_path,
                align=Align.CENTER,
            )
        outline = _bold_text_outline(outline, stamp.bold_amount)
        outline = outline.mirror(Plane.YZ)
        cutter = extrude(outline, amount=stamp.depth + 0.01, dir=(0, 0, 1))
        cutter = (
            Pos(stamp.x, stamp.y, -0.01)
            * Rot(0, 0, stamp.rotation)
            * Pos(0, line_offset, 0)
            * cutter
        )
        text_cutters.append(cutter)
        yield cutter

    if stamp.frame_width > 0:
        yield _brand_frame_cutter(
            text_cutters[:2],
            stamp,
        )
        yield _brand_frame_cutter((text_cutters[2],), stamp)


def column_solid(column: RetainerColumn):
    """A post with a lip that overhangs the pedal side."""
    dx, dy = DIRECTIONS[column.facing]
    post = Box(column.thickness, column.depth, column.height, align=BOTTOM)
    post = Pos(column.x + dx * column.thickness / 2.0, column.y + dy * column.thickness / 2.0, 0) * post
    lip = Box(column.lip, column.depth, column.thickness, align=BOTTOM)
    lip = Pos(column.x - dx * column.lip / 2.0, column.y - dy * column.lip / 2.0,
              column.height - column.thickness) * lip
    return post + lip


def ring_reach(spec: KeeperSpec, arch_scale: float = 1.0, width: float | None = None) -> float:
    """How far one ring reaches outboard of its post face."""
    ring = build_ring(spec, arch_scale=arch_scale, width=width)
    return abs(ring.bounding_box().min.X)


def build_spine(
    spine: SpineSpec,
    spec: KeeperSpec | None = None,
    include_bar: bool = True,
) -> tuple[object, list[float], float]:
    """One spine: `clips` keepers on an axis, strung by a bar.

    Clip post faces land exactly `post_spacing` apart, so the spine drops into the
    slot grid with no arithmetic in between. Returns the solid, those post-face
    positions along the spine axis, and the ring reach outboard of them.

    `include_bar=False` leaves the bar out: use it when a wing already covers the
    spine, otherwise the bar's faces land coincident with the plate's.
    """
    s = spec or load_spec()
    n = spine.clips
    if n < 1:
        raise ValueError("a spine needs at least one clip")

    positions = [(i - (n - 1) / 2.0) * spine.post_spacing for i in range(n)]
    reach = ring_reach(s, spine.arch_scale, spine.clip_width)

    part = None
    for p in positions:
        mirrored = spine.flare == "outward" and p > 0
        ring = build_ring(s, mirror=mirrored, arch_scale=spine.arch_scale, width=spine.clip_width)
        ring = Pos(p, 0.0, 0.0) * ring
        part = ring if part is None else part + ring

    if include_bar:
        bar_len = abs(positions[-1] - positions[0]) + s.post_t
        part = part + Box(bar_len, spine.clip_width, s.bar_t, align=BOTTOM)

    if spine.axis == "y":
        part = Rot(0, 0, 90) * part
        part = Pos(spine.offset, 0.0, 0.0) * part
    else:
        part = Pos(0.0, spine.offset, 0.0) * part
    return part, positions, reach


def _clearance_cut(
    spine: SpineSpec,
    post_face: float,
    reach: float,
    spec: KeeperSpec,
    thickness: float,
    limit: float | None = None,
):
    """The plate slot that lets a clip flex outward.

    Runs from the clip's post face, past the arch, and spans the clip width so the
    clip is not boxed in - the two notches either side of the spine in the OEM part.
    `limit` is the plate edge along the spine axis: if the notch would stop within
    3 mm of it, run it through the edge instead of leaving a fragile web.
    """
    sign = 1.0 if post_face >= 0 else -1.0
    # Keep the plate land beneath the full post; clearance starts at its outer face.
    start = abs(post_face) + spec.post_t
    length = reach - spec.post_t + spine.clearance
    depth = spine.clip_width + spine.clearance_width
    radius = spine.clearance_radius
    if radius < 0 or radius > min(length, depth) / 2.0:
        raise ValueError("clearance radius must be between zero and half the notch dimensions")
    if limit is not None:
        edge = abs(limit)
        if start + length > edge - 3.0:
            length = edge + radius + 0.5 - start
    if radius > 0:
        sketch = RectangleRounded(length, depth, radius)
    else:
        sketch = Rectangle(length, depth)
    cutter = extrude(sketch, amount=thickness + 2.0)
    mid = start + length / 2.0
    if spine.axis == "x":
        return Pos(sign * mid, spine.offset, -1.0) * cutter
    return Pos(spine.offset, sign * mid, -1.0) * (Rot(0, 0, 90) * cutter)


def build_mount(mount: MountSpec, spec: KeeperSpec | None = None):
    """Union the wings and spines into one solid, minus clip clearance and holes."""
    s = spec or load_spec()
    part = None

    for wing in mount.wings:
        plate = _plate(wing, mount.thickness)
        for pocket in wing.pockets:
            plate = plate - _pocket_cutter(pocket, mount.thickness)
        part = plate if part is None else part + plate

    for spine in mount.spines:
        idx = 0 if spine.axis == "x" else 1
        edge = max((abs(p[idx]) for w in mount.wings for p in w.points()), default=None)
        spine_solid, post_faces, reach = build_spine(spine, s, include_bar=part is None)
        if part is not None:
            for face in post_faces:
                part = part - _clearance_cut(spine, face, reach, s, mount.thickness, edge)
        part = spine_solid if part is None else part + spine_solid

    columns = list(mount.columns)
    for wing in mount.wings:
        columns.extend(wing.columns)
    for column in columns:
        solid = column_solid(column)
        part = solid if part is None else part + solid

    holes = list(mount.holes)
    for wing in mount.wings:
        holes.extend(wing.holes)
    for hole in holes:
        part = part - _csk_cutter(hole, mount.thickness)

    if mount.brand_stamp is not None:
        if mount.brand_stamp.depth >= mount.thickness:
            raise ValueError("brand stamp depth must be less than the plate thickness")
        for cutter in _brand_stamp_cutters(mount.brand_stamp):
            part = part - cutter

    if part is None:
        raise ValueError("mount has no spines, wings or columns")
    return part
