"""Generate the board-side base plate for one 125B: the Type B1 plate, clips off.

This is step one of the single-125B riser, the part that mixes two reference
families:

* ``enclosure_125b`` supplies the plate: a 72 x 125.5 x 3 mm lobed outline
  carrying one 125B pedal's own fasteners - four Ø4 clearance holes with Ø6.8
  counterbores, four Ø3.5 snaps with Ø5.8 spot-faces, and one Ø3.5 each side,
  every recess on the board face;
* ``stepup_risers`` supplies the job: a riser that clips to the board and carries
  a pedal above it.

This base is neither of those yet. It is the B1 plate with both integral C-loops
removed and, with them, the 24.6 x 21.9 end window that only exists to free the
clip's blade. What is left is the outline and the fastener field: a flat plate to
sign off before a body is stood on it or a clip hung under it.

No plate dimension is restated here. ``cfg/single_125b.json`` points at
``enclosure_125b/cfg/enclosure_125b.json`` and the outline, thickness, patterns
and material are read from it at load time, the same way the enclosure plate
reads the retainer section from ``commons``.

Datum is the enclosure plate's: origin at the centre of the board-facing face,
+X across the 67 mm width, +Y along the 125.5 mm length, +Z from the board toward
the pedal. The plate occupies z = 0..3 and nothing sits below z = 0.

    .venv/Scripts/python stepup_risers/src/single_125b.py
    .venv/Scripts/python stepup_risers/src/single_125b.py --check
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from dataclasses import dataclass

import cadquery as cq

PROJECT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT / "cfg" / "single_125b.json"
DWG = PROJECT / "dwg"

LEN_TOL_MM = 0.02

# Slack for booleans and for the inspect-by-section probes. None of these are part
# dimensions: they only have to clear a face and be small enough not to change what
# a cut or a probe selects.
CUT_MARGIN_MM = 1.0
PROBE_STEP_MM = 0.25
PROBE_REACH_MM = 1.0
PROBE_HALF_MM = 0.5


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Pattern:
    """One screw pattern: holes at ±x, ±y, recessed on one face.

    `face_side` says which face the counterbore or spot-face opens on; the B1
    sheets print its 1.5 depth but not which way round it goes.
    """

    id: str
    count: int
    bore_mm: float
    x_mm: float
    y_mm: float
    face_mm: float | None = None
    face_depth_mm: float = 0.0
    face_side: str = "board"

    @property
    def positions(self) -> list[tuple[float, float]]:
        if self.count == 2:
            return [(-self.x_mm, self.y_mm), (self.x_mm, self.y_mm)]
        return [
            (-self.x_mm, -self.y_mm),
            (self.x_mm, -self.y_mm),
            (-self.x_mm, self.y_mm),
            (self.x_mm, self.y_mm),
        ]


@dataclass(frozen=True)
class Spec:
    raw: dict
    id: str
    plate_source: pathlib.Path
    length_mm: float
    side_width_mm: float
    width_mm: float
    lobe_radius_mm: float
    lobe_x_mm: float
    lobe_y_mm: float
    boss_radius_mm: float
    boss_x_mm: float
    boss_y_mm: float
    thickness_mm: float
    window_width_mm: float
    window_depth_mm: float
    patterns: list[Pattern]
    material_id: str
    density_g_cm3: float

    @property
    def half_length_mm(self) -> float:
        return self.length_mm / 2.0

    @property
    def half_side_mm(self) -> float:
        return self.side_width_mm / 2.0

    @property
    def side_edge_top_mm(self) -> float:
        """Where a corner lobe crosses the straight side, so the side edge starts."""
        dx = self.half_side_mm - self.lobe_x_mm
        return self.lobe_y_mm - math.sqrt(self.lobe_radius_mm**2 - dx**2)

    @property
    def boss_edge_mm(self) -> float:
        dx = self.half_side_mm - self.boss_x_mm
        return math.sqrt(self.boss_radius_mm**2 - dx**2)


def _read(path: pathlib.Path, what: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{what} is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _pattern(node: dict, key: str, face_key: str) -> Pattern:
    side = str(node.get(face_key.replace("_mm", "_face"), "board"))
    if side not in ("pedal", "board"):
        raise ValueError(f"{key} {face_key} face must be pedal or board, not {side!r}")
    return Pattern(
        id=key,
        count=int(node["count"]),
        bore_mm=float(node["bore_mm"]),
        x_mm=float(node["x_mm"]),
        y_mm=float(node["y_mm"]),
        face_mm=float(node[face_key]) if face_key in node else None,
        face_depth_mm=float(
            node.get("counterbore_depth_mm", node.get("spotface_depth_mm", 0.0))
        ),
        face_side=side,
    )


def load(path: pathlib.Path = DEFAULT_CONFIG) -> Spec:
    raw = _read(path, path.name)
    plate_path = (PROJECT / raw["plate"]["from"]).resolve()
    plate_raw = _read(plate_path, f"{path.name}: plate source")
    mount = plate_raw["mount"]
    outline = mount["outline"]
    holes = mount["holes"]

    departures = raw["departures"]
    clips = str(departures["clips"]["mode"])
    window = str(departures["end_window"]["mode"])
    if clips != "removed":
        raise ValueError(f"{path.name}: clips.mode has to be 'removed', not {clips!r}")
    if window != "closed":
        raise ValueError(
            f"{path.name}: end_window.mode has to be 'closed' for a clip-free base, "
            f"not {window!r}"
        )

    material = plate_raw["material"]
    presets_path = (plate_path.parents[1] / material["presets_from"]).resolve()
    presets = _read(presets_path, f"{path.name}: material presets")["material"][
        "presets"
    ]
    material_id = str(material["id"])
    if material_id not in presets:
        raise KeyError(f"{presets_path.name}: no preset for material {material_id!r}")

    return Spec(
        raw=raw,
        id=str(raw["id"]),
        plate_source=plate_path,
        length_mm=float(outline["length_mm"]),
        side_width_mm=float(outline["side_width_mm"]),
        width_mm=float(outline["width_over_lobes_mm"]),
        lobe_radius_mm=float(outline["corner_lobe_radius_mm"]),
        lobe_x_mm=float(outline["corner_lobe_x_mm"]),
        lobe_y_mm=float(outline["corner_lobe_y_mm"]),
        boss_radius_mm=float(outline["side_boss_radius_mm"]),
        boss_x_mm=float(holes["side"]["x_mm"]),
        boss_y_mm=float(holes["side"]["y_mm"]),
        thickness_mm=float(mount["plate_thickness_mm"]),
        window_width_mm=float(outline["end_window"]["width_mm"]),
        window_depth_mm=float(outline["end_window"]["depth_mm"]),
        patterns=[
            _pattern(holes["clearance"], "clearance", "counterbore_mm"),
            _pattern(holes["snap"], "snap", "spotface_mm"),
            _pattern(holes["side"], "side", "spotface_mm"),
        ],
        material_id=material_id,
        density_g_cm3=float(presets[material_id]["density_g_cm3"]),
    )


# --------------------------------------------------------------------------- #
# geometry helpers
# --------------------------------------------------------------------------- #


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> cq.Solid:
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def _cylinder(dia: float, z0: float, z1: float, x: float, y: float) -> cq.Solid:
    return cq.Solid.makeCylinder(
        dia / 2.0, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1)
    )


def _cut(wp: cq.Workplane, tools: list[cq.Solid]) -> cq.Workplane:
    if not tools:
        return wp
    stack = cq.Workplane("XY")
    for tool in tools:
        stack = stack.add(tool)
    return wp.cut(stack)


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #


def outline_profile(spec: Spec) -> cq.Workplane:
    """The B1 silhouette: straight sides, four lobes and the two side bosses.

    Every arc is centred on the feature it protects - a lobe on its snap hole, a
    boss on its side hole - which is what makes the 67 mm sides and the 72 mm over
    the lobes close against the printed 125.5 mm. Nothing here knows about the
    clips, so the profile is the enclosure plate's own, unchanged.
    """
    hx, hy = spec.half_side_mm, spec.half_length_mm
    lx, ly, lr = spec.lobe_x_mm, spec.lobe_y_mm, spec.lobe_radius_mm
    top = spec.side_edge_top_mm
    boss = spec.boss_edge_mm
    bx, by, br = spec.boss_x_mm, spec.boss_y_mm, spec.boss_radius_mm

    wp = cq.Workplane("XY").moveTo(0.0, hy)
    wp = wp.lineTo(lx, hy)
    wp = wp.threePointArc((lx + lr, ly), (hx, top))
    wp = wp.lineTo(hx, by + boss)
    wp = wp.threePointArc((bx + br, by), (hx, by - boss))
    wp = wp.lineTo(hx, -top)
    wp = wp.threePointArc((lx + lr, -ly), (lx, -hy))
    wp = wp.lineTo(-lx, -hy)
    wp = wp.threePointArc((-lx - lr, -ly), (-hx, -top))
    wp = wp.lineTo(-hx, by - boss)
    wp = wp.threePointArc((-bx - br, by), (-hx, by + boss))
    wp = wp.lineTo(-hx, top)
    wp = wp.threePointArc((-lx - lr, ly), (-lx, hy))
    return wp.close()


def build_base(spec: Spec) -> cq.Workplane:
    """The bare plate: the lobed outline, drilled and recessed, and nothing else."""
    plate = outline_profile(spec).extrude(spec.thickness_mm)
    thickness = spec.thickness_mm

    tools: list[cq.Solid] = []
    for pattern in spec.patterns:
        for x, y in pattern.positions:
            tools.append(
                _cylinder(
                    pattern.bore_mm, -CUT_MARGIN_MM, thickness + CUT_MARGIN_MM, x, y
                )
            )
            if pattern.face_mm and pattern.face_depth_mm:
                if pattern.face_side == "board":
                    z0, z1 = -CUT_MARGIN_MM, pattern.face_depth_mm
                else:
                    z0, z1 = (
                        thickness - pattern.face_depth_mm,
                        thickness + CUT_MARGIN_MM,
                    )
                tools.append(_cylinder(pattern.face_mm, z0, z1, x, y))

    return _cut(plate, tools).clean()


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #


@dataclass
class Check:
    name: str
    value: str
    limit: str
    ok: bool
    note: str = ""


def _pieces(solid: cq.Solid, x0, x1, y0, y1, z0, z1) -> list:
    cut = solid.intersect(_box(x0, x1, y0, y1, z0, z1))
    return sorted((s.BoundingBox() for s in cut.Solids()), key=lambda b: b.xmin)


def _bore_faces(solid: cq.Solid, dia: float, tol: float = 0.01) -> list:
    faces = []
    for face in solid.Faces():
        if face.geomType() != "CYLINDER":
            continue
        radius = face._geomAdaptor().Cylinder().Radius()
        if abs(2.0 * radius - dia) <= tol:
            faces.append(face)
    return faces


def _bores_at(solid: cq.Solid, dia: float, y_mm: float) -> list[tuple[float, float]]:
    """That diameter on the row at ±|y|, so the two Ø3.5 patterns stay apart."""
    return [
        (f.Center().x, f.Center().y)
        for f in _bore_faces(solid, dia)
        if abs(abs(f.Center().y) - abs(y_mm)) < 0.5
    ]


def _pitch(values: list[float]) -> float:
    return max(values) - min(values)


def validate(spec: Spec, base: cq.Workplane) -> list[Check]:
    solid = base.val()
    box = solid.BoundingBox()
    checks: list[Check] = []

    x0, x1 = box.xmin - PROBE_REACH_MM, box.xmax + PROBE_REACH_MM
    mid_z = spec.thickness_mm / 2.0

    def exact(name, value, wanted, note=""):
        checks.append(
            Check(
                name,
                f"{value:.2f} mm",
                f"{wanted:.2f} mm",
                abs(value - wanted) <= LEN_TOL_MM,
                note,
            )
        )

    def flag(name, value, limit, ok, note=""):
        checks.append(Check(name, value, limit, bool(ok), note))

    mid = _pieces(
        solid,
        x0,
        x1,
        -PROBE_STEP_MM,
        PROBE_STEP_MM,
        mid_z - PROBE_STEP_MM,
        mid_z + PROBE_STEP_MM,
    )[0]

    exact(
        "overall width over the lobes",
        box.xlen,
        spec.width_mm,
        "72.0 on both B1 sheets",
    )
    exact("overall length", box.ylen, spec.length_mm, "125.5 on the alt side view")
    exact(
        "plate thickness",
        box.zlen,
        spec.thickness_mm,
        "3 printed on section B-B",
    )
    exact(
        "side width",
        mid.xlen,
        spec.side_width_mm,
        "67 between the straight sides on both sheets",
    )
    exact(
        "lobe protrusion",
        (box.xlen - mid.xlen) / 2.0,
        (spec.width_mm - spec.side_width_mm) / 2.0,
        "the corner lobes standing proud of the straight sides",
    )
    exact(
        "board face on the datum",
        box.zmin,
        0.0,
        "clips removed: nothing of this base sits below its own board face",
    )

    # The B1 window is cut through and open to the end edge, so on the plate it
    # stands in a centre strip across its depth comes back empty. Here it has to be
    # material all the way to the end edge.
    band_end = spec.half_length_mm + PROBE_REACH_MM
    band_start = spec.half_length_mm - spec.window_depth_mm + PROBE_STEP_MM
    closed = _pieces(
        solid,
        -PROBE_HALF_MM,
        PROBE_HALF_MM,
        band_start,
        band_end,
        mid_z - PROBE_STEP_MM,
        mid_z + PROBE_STEP_MM,
    )
    flag(
        "end window closed",
        f"{len(closed)} solid(s)",
        "1",
        len(closed) == 1,
        f"the {spec.window_width_mm:.1f} x {spec.window_depth_mm:.1f} end window goes "
        "with the clip that needed it; open to the end edge it would return nothing here",
    )
    if closed:
        exact(
            "end material reaches the edge",
            closed[0].ymax,
            spec.half_length_mm,
            "the closed end runs out to the plate's own end edge",
        )

    for pattern in spec.patterns:
        bores = _bores_at(solid, pattern.bore_mm, pattern.y_mm)
        flag(
            f"{pattern.id} holes",
            str(len(bores)),
            str(pattern.count),
            len(bores) == pattern.count,
            f"Ø{pattern.bore_mm:g} at ({pattern.x_mm:.2f}, ±{abs(pattern.y_mm):.2f})",
        )
        xs = [x for x, _ in bores] or [0.0]
        ys = [y for _, y in bores] or [0.0]
        exact(f"{pattern.id} pitch across", _pitch(xs), 2.0 * pattern.x_mm)
        if pattern.count == 4:
            exact(f"{pattern.id} pitch along", _pitch(ys), 2.0 * pattern.y_mm)
        if pattern.face_mm:
            faces = _bore_faces(solid, pattern.face_mm)
            faces = [
                f for f in faces if abs(abs(f.Center().y) - abs(pattern.y_mm)) < 0.5
            ]
            flag(
                f"{pattern.id} recesses",
                str(len(faces)),
                str(pattern.count),
                len(faces) == pattern.count,
                f"Ø{pattern.face_mm:g} x {pattern.face_depth_mm:g} deep, {pattern.face_side} side",
            )
            want = (
                spec.thickness_mm - pattern.face_depth_mm / 2.0
                if pattern.face_side == "pedal"
                else pattern.face_depth_mm / 2.0
            )
            worst = max((abs(f.Center().z - want) for f in faces), default=float("nan"))
            flag(
                f"{pattern.id} face side",
                f"{sum(f.Center().z for f in faces) / len(faces):.2f} mm"
                if faces
                else "-",
                f"{want:.2f} mm",
                worst <= LEN_TOL_MM,
                f"recess centre has to sit on the {pattern.face_side} side",
            )

    flag(
        "solid count",
        str(len(solid.Solids())),
        "1",
        len(solid.Solids()) == 1,
        "the base is one plate; the clips are not part of it",
    )
    mass = solid.Volume() / 1000.0 * spec.density_g_cm3
    flag(
        "volume",
        f"{solid.Volume():.0f} mm3",
        "> 0",
        solid.Volume() > 0.0,
        f"{mass:.1f} g in {spec.material_id}",
    )
    return checks


def report(spec: Spec, checks: list[Check], out: pathlib.Path | None) -> str:
    lines = [
        f"{spec.id} base{'  (' + pathlib.Path(out).name + ')' if out else ''}",
        "",
        f"plate, read from {spec.plate_source.parents[1].name}/cfg/{spec.plate_source.name}",
        f"  length                {spec.length_mm:7.2f} mm   125.5, alt side view",
        f"  width over the lobes  {spec.width_mm:7.2f} mm   72, both sheets",
        f"  width between sides   {spec.side_width_mm:7.2f} mm   67, both sheets",
        f"  thickness             {spec.thickness_mm:7.2f} mm   3, section B-B",
        (
            f"  corner lobes          r {spec.lobe_radius_mm:.2f} about "
            f"({spec.lobe_x_mm:+.2f}, {spec.lobe_y_mm:+.2f}), "
            f"{(spec.width_mm - spec.side_width_mm) / 2.0:.1f} proud of each side"
        ),
        (
            f"  side bosses           r {spec.boss_radius_mm:.2f} at "
            f"({spec.boss_x_mm:+.2f}, {spec.boss_y_mm:+.2f})"
        ),
        (
            f"  end window            closed, was {spec.window_width_mm:.1f} x "
            f"{spec.window_depth_mm:.1f}; no clip, no window"
        ),
        "",
        "screws",
    ]
    for pattern in spec.patterns:
        face = (
            f", Ø{pattern.face_mm:g} recess {pattern.face_depth_mm:g} deep on the "
            f"{pattern.face_side} side"
            if pattern.face_mm
            else ""
        )
        lines.append(
            f"  {pattern.id:<10} {pattern.count:2d} x Ø{pattern.bore_mm:g} at "
            f"({pattern.x_mm:.2f}, {pattern.y_mm:.2f}){face}"
        )
    lines += ["", "removed from the B1 plate"]
    for key in ("clips", "end_window"):
        node = spec.raw["departures"][key]
        lines.append(f"  {key:<10} {node['mode']:<8} {node['note']}")
    lines += ["", "checks"]

    width = max(len(c.name) for c in checks)
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        lines.append(
            f"  {mark} {c.name:<{width}}  {c.value:>14}  {c.limit:>14}  {c.note}"
        )
    failed = [c for c in checks if not c.ok]
    lines.append("")
    lines.append(
        f"{len(checks) - len(failed)}/{len(checks)} checks pass"
        if not failed
        else f"{len(failed)} CHECK(S) FAILED"
    )
    return "\n".join(lines)


def summary(spec: Spec, checks: list[Check], out: pathlib.Path) -> dict:
    return {
        "id": spec.id,
        "stl": str(out),
        "plate_mm": {
            "length": spec.length_mm,
            "width_over_lobes": spec.width_mm,
            "side_width": spec.side_width_mm,
            "thickness": spec.thickness_mm,
        },
        "screw_patterns": {
            p.id: {
                "count": p.count,
                "bore": p.bore_mm,
                "x": p.x_mm,
                "y": p.y_mm,
                "recess": p.face_mm,
                "recess_depth": p.face_depth_mm,
                "recess_side": p.face_side,
            }
            for p in spec.patterns
        },
        "removed": {
            "clips": spec.raw["departures"]["clips"]["mode"],
            "end_window": spec.raw["departures"]["end_window"]["mode"],
        },
        "checks": [
            {"name": c.name, "value": c.value, "limit": c.limit, "ok": c.ok}
            for c in checks
        ],
        "ok": all(c.ok for c in checks),
    }


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def export(shape: cq.Workplane, out: pathlib.Path, tolerance: float) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(shape, str(out), tolerance=tolerance, angularTolerance=0.1)
    cq.exporters.export(shape, str(out.with_suffix(".step")))
    print(f"wrote {out}")
    print(f"wrote {out.with_suffix('.step')}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    ap.add_argument(
        "--part",
        choices=("base",),
        default="base",
        help="only the base exists in step one; later steps add the body and clips",
    )
    ap.add_argument(
        "--out",
        type=pathlib.Path,
        default=DWG / "single_125b_base.stl",
        help="STL to write, with the STEP beside it",
    )
    ap.add_argument("--check", action="store_true", help="report the checks only")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    ap.add_argument(
        "--tolerance", type=float, default=0.01, help="STL linear tolerance"
    )
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    spec = load(args.config)
    base = build_base(spec)
    checks = validate(spec, base)
    ok = all(c.ok for c in checks)

    if args.json:
        print(json.dumps(summary(spec, checks, args.out), indent=2))
    else:
        print(report(spec, checks, None if args.check else args.out))
    if not args.check:
        export(base, args.out, args.tolerance)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
