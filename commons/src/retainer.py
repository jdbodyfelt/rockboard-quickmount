"""Generate the QuickMount retainer.

The retainer is the pressure-locking C-loop under every QuickMount plate: a stout
post hangs from the plate, the arch springs across below the board, and a thin
blade comes back up through the next slot with a ledge that hooks under the sheet.
`cfg/retainer.json` holds the measured section and says where each number came
from; this module turns it into a solid and answers for the fits it implies.

    .venv/Scripts/python commons/src/retainer.py
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

COMMONS = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = COMMONS / "cfg" / "retainer.json"
DEFAULT_STL = COMMONS / "dwg" / "retainer.stl"

LEN_TOL_MM = 0.02


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Ledge:
    drop_below_plate_mm: float
    protrusion_mm: float


@dataclass(frozen=True)
class Spec:
    """Everything the generator needs, resolved and cross-checked."""

    raw: dict
    width_mm: float
    outer_width_mm: float
    height_total_mm: float
    plate_thickness_mm: float
    drop_below_plate_top_mm: float
    mouth_width_mm: float
    post_wall_mm: float
    blade_wall_mm: float
    blade_tip_chamfer_mm: float
    ledge: Ledge
    spread_mm: float
    wall_min_mm: float
    material_id: str
    elastic_modulus_mpa: float
    yield_strain_percent: float
    safety_factor: float
    density_g_cm3: float

    # ---- geometry --------------------------------------------------------- #

    @property
    def loop_drop_mm(self) -> float:
        """Plate underside (z = 0) to the loop's lowest point, positive down."""
        return self.drop_below_plate_top_mm - self.plate_thickness_mm

    @property
    def half_mouth_mm(self) -> float:
        return self.mouth_width_mm / 2.0

    @property
    def half_outer_mm(self) -> float:
        return self.outer_width_mm / 2.0

    @property
    def blade_outer_half_mm(self) -> float:
        return self.half_mouth_mm + self.blade_wall_mm

    @property
    def blade_outer_width_mm(self) -> float:
        """Width the blade presents above the ledge."""
        return 2.0 * self.blade_outer_half_mm

    @property
    def arch_centre_z_mm(self) -> float:
        """Arch centre. Placing it here makes the arch a semicircle of constant wall."""
        return -(self.loop_drop_mm - self.half_outer_mm)

    @property
    def arch_wall_mm(self) -> float:
        return self.half_outer_mm - self.half_mouth_mm

    @property
    def ledge_z_mm(self) -> float:
        """Upward face of the ledge, the one that catches the sheet's underside."""
        return -self.ledge.drop_below_plate_mm

    @property
    def arm_depth_below_ledge_mm(self) -> float:
        """How much straight arm stands between the ledge and the arch centre."""
        return abs(self.arch_centre_z_mm) - self.ledge.drop_below_plate_mm

    # ---- the joint it makes ----------------------------------------------- #

    @property
    def lock_mm(self) -> float:
        """The ledge's reach under the sheet, which is its protrusion."""
        return self.half_outer_mm - self.blade_outer_half_mm

    @property
    def overall_with_ear_mm(self) -> float:
        return self.drop_below_plate_top_mm + float(
            self.raw["envelope"].get("ear_above_plate_mm") or 0.0
        )

    # ---- bend tolerance --------------------------------------------------- #

    @property
    def flexure_length_mm(self) -> float:
        """Developed centreline of the compliant loop: both legs plus the arch."""
        mid_radius = (self.half_mouth_mm + self.half_outer_mm) / 2.0
        straight = 2.0 * (self.plate_thickness_mm + abs(self.arch_centre_z_mm))
        return straight + math.pi * mid_radius

    @property
    def bend_wall_mm(self) -> float:
        """The ledge sits at the arch end of the blade, so the arch has to bend."""
        return max(self.post_wall_mm, self.arch_wall_mm)

    @property
    def allowable_strain(self) -> float:
        return self.yield_strain_percent / 100.0 / self.safety_factor

    @property
    def predicted_strain(self) -> float:
        return 1.5 * self.bend_wall_mm * self.spread_mm / (self.flexure_length_mm**2)

    @property
    def predicted_stress_mpa(self) -> float:
        return self.predicted_strain * self.elastic_modulus_mpa

    @property
    def yield_stress_mpa(self) -> float:
        return self.yield_strain_percent * self.elastic_modulus_mpa / 100.0

    @property
    def min_flexure_length_mm(self) -> float:
        return math.sqrt(1.5 * self.bend_wall_mm * self.spread_mm / self.allowable_strain)

    @property
    def opening_force_n(self) -> float:
        """Cantilever estimate over the developed loop; an upper bound, not a spec."""
        inertia = self.width_mm * self.bend_wall_mm**3 / 12.0
        return (
            3.0
            * self.elastic_modulus_mpa
            * inertia
            * self.spread_mm
            / (self.flexure_length_mm**3)
        )


def load(path: Path = DEFAULT_CONFIG) -> Spec:
    raw = json.loads(path.read_text(encoding="utf-8"))

    def need(*keys):
        node = raw
        for key in keys:
            if key not in node:
                raise KeyError(f"{path.name}: missing {'.'.join(keys)}")
            node = node[key]
        return node

    env, sec, joint, ledge = (
        need("envelope"),
        need("section"),
        need("joint"),
        need("section", "ledge"),
    )
    material = need("material")
    presets = material["presets"]
    if material["id"] not in presets:
        raise KeyError(f"{path.name}: material.id {material['id']!r} has no preset")
    preset = presets[material["id"]]

    return Spec(
        raw=raw,
        width_mm=float(env["width_mm"]),
        outer_width_mm=float(env["outer_width_mm"]),
        height_total_mm=float(env["drop_below_plate_top_mm"]),
        plate_thickness_mm=float(env["plate_thickness_mm"]),
        drop_below_plate_top_mm=float(env["drop_below_plate_top_mm"]),
        mouth_width_mm=float(sec["mouth_width_mm"]),
        post_wall_mm=float(sec["post_wall_mm"]),
        blade_wall_mm=float(sec["blade_wall_mm"]),
        blade_tip_chamfer_mm=float(sec["blade_tip_chamfer_mm"]),
        ledge=Ledge(
            drop_below_plate_mm=float(ledge["drop_below_plate_mm"]),
            protrusion_mm=float(ledge["protrusion_mm"]),
        ),
        spread_mm=float(joint["spread_mm"]),
        wall_min_mm=float(joint["wall_min_mm"]),
        material_id=str(material["id"]),
        elastic_modulus_mpa=float(preset["elastic_modulus_mpa"]),
        yield_strain_percent=float(preset["yield_strain_percent"]),
        safety_factor=float(material["safety_factor"]),
        density_g_cm3=float(preset["density_g_cm3"]),
    )


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #

# A segment is ("L", x, z) or ("A", x, z, mid_x, mid_z) in the section plane.
Segment = tuple


def _section(segments: list[Segment], width_mm: float) -> cq.Workplane:
    """Extrude a closed (x, z) section across `width_mm` on y, centred on y = 0."""
    first = segments[0]
    wp = cq.Workplane("XZ").moveTo(first[1], first[2])
    for seg in segments[1:]:
        if seg[0] == "L":
            wp = wp.lineTo(seg[1], seg[2])
        else:
            wp = wp.threePointArc((seg[3], seg[4]), (seg[1], seg[2]))
    wp = wp.close().extrude(width_mm)
    box = wp.val().BoundingBox()
    return wp.translate((0.0, -(box.ymin + box.ymax) / 2.0, 0.0))


def loop_section(spec: Spec) -> tuple[list[Segment], list[Segment]]:
    """The loop's outer silhouette and the mouth cut out of it.

    Reading the silhouette from the +x post, over the top of the mouth and down the
    blade: the post is square to the plate, the arch is a semicircle of constant
    wall, and the blade is thin until the ledge, where it steps out to the full
    footprint and stays that way down to the arch.
    """
    xo, xm = spec.half_outer_mm, spec.half_mouth_mm
    top = spec.plate_thickness_mm
    za = spec.arch_centre_z_mm
    bottom = -spec.loop_drop_mm
    xb = spec.blade_outer_half_mm
    zl = spec.ledge_z_mm
    ch = spec.blade_tip_chamfer_mm

    outer = [
        ("L", xo, top),
        ("L", xo, za),
        ("A", -xo, za, 0.0, bottom),
        ("L", -xo, zl),
        ("L", -xb, zl),          # the ledge, facing the plate
        ("L", -xb, top - ch),
        ("L", -xb + ch, top),    # corner break on the blade tip
    ]
    # the mouth runs past the top face so the cut is open rather than coplanar
    mouth = [
        ("L", xm, top + 1.0),
        ("L", xm, za),
        ("A", -xm, za, 0.0, bottom + spec.arch_wall_mm),
        ("L", -xm, top + 1.0),
    ]
    return outer, mouth


def build(spec: Spec) -> cq.Workplane:
    outer, mouth = loop_section(spec)
    return _section(outer, spec.width_mm).cut(_section(mouth, spec.width_mm)).clean()


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


def validate(spec: Spec, part: cq.Workplane) -> list[Check]:
    box = part.val().BoundingBox()
    checks: list[Check] = []

    def exact(name, value, wanted, note=""):
        checks.append(
            Check(name, f"{value:.2f} mm", f"{wanted:.2f} mm", abs(value - wanted) <= LEN_TOL_MM, note)
        )

    def atleast(name, value, floor, note=""):
        checks.append(Check(name, f"{value:.2f} mm", f">= {floor:.2f} mm", value >= floor, note))

    def flag(name, value, limit, ok, note=""):
        checks.append(Check(name, value, limit, bool(ok), note))

    exact("height over all", box.zlen, spec.height_total_mm)
    exact("outer width", box.xlen, spec.outer_width_mm, "19.0 with calipers on a Type E; neither Type A nor Type E prints it")
    exact("width along slot", box.ylen, spec.width_mm, "the 22 mm callout, printed on A and E")
    exact("loop below plate underside", -box.zmin, spec.loop_drop_mm)
    exact("legs stop at the plate top", box.zmax, spec.plate_thickness_mm)
    exact(
        "drop below plate top",
        box.zlen,
        spec.drop_below_plate_top_mm,
        "18.89 on the Type A front view and on the A/D/H/M end views",
    )
    exact("arch wall", spec.arch_wall_mm, spec.half_outer_mm - spec.half_mouth_mm)
    exact(
        "mouth from footprint",
        spec.mouth_width_mm,
        spec.outer_width_mm
        - spec.post_wall_mm
        - spec.ledge.protrusion_mm
        - spec.blade_wall_mm,
        "one side is the post at the envelope, the other is the blade inset by the ledge",
    )
    exact(
        "ledge drop",
        abs(spec.ledge_z_mm),
        spec.ledge.drop_below_plate_mm,
        "the one dimension the board has to agree with",
    )
    exact(
        "ledge protrusion",
        spec.half_outer_mm - spec.blade_outer_half_mm,
        spec.ledge.protrusion_mm,
    )
    atleast(
        "blade wall",
        spec.blade_wall_mm,
        spec.wall_min_mm,
        "thin on purpose: it is what lets the ledge pass a sheet edge",
    )
    atleast(
        "post wall",
        spec.post_wall_mm,
        2.0 * spec.wall_min_mm,
        "the rigid side of the loop; the pedal load runs through it",
    )
    atleast(
        "ledge bite",
        spec.lock_mm,
        0.5,
        "how far the ledge reaches under the sheet",
    )
    atleast(
        "arm below the ledge",
        spec.arm_depth_below_ledge_mm,
        2.0,
        "the step needs a solid column behind it to carry the bite",
    )
    atleast(
        "flexure length",
        spec.flexure_length_mm,
        spec.min_flexure_length_mm,
        "developed loop; the blade alone is not a valid flexure",
    )
    flag(
        "bend strain",
        f"{spec.predicted_strain * 100:.2f} %",
        f"<= {spec.allowable_strain * 100:.2f} %",
        spec.predicted_strain <= spec.allowable_strain,
        f"{spec.material_id}, safety factor {spec.safety_factor:g}",
    )
    flag(
        "bend stress",
        f"{spec.predicted_stress_mpa:.1f} MPa",
        f"<= {spec.yield_stress_mpa / spec.safety_factor:.1f} MPa",
        spec.predicted_stress_mpa <= spec.yield_stress_mpa / spec.safety_factor,
        "yield stress over the safety factor",
    )
    exact(
        "overall with the ear",
        spec.overall_with_ear_mm,
        21.19,
        "Type H's overall callout, which is 18.89 + a 2.30 ear",
    )
    flag(
        "solid count",
        str(len(part.solids().vals())),
        "1",
        len(part.solids().vals()) == 1,
        "post, arch and blade have to fuse",
    )
    flag(
        "volume",
        f"{part.val().Volume():.0f} mm3",
        "> 0",
        part.val().Volume() > 0.0,
        f"{part.val().Volume() / 1000.0 * spec.density_g_cm3:.1f} g in {spec.material_id}",
    )
    return checks


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #


def report(spec: Spec, checks: list[Check], out: Path) -> str:
    lines = [
        f"retainer  ({Path(out).name})",
        "",
        "envelope, drawn from the Type A / Type E sheets plus calipers",
        f"  width along slot      {spec.width_mm:7.2f} mm   22, printed on A and E",
        f"  outer width           {spec.outer_width_mm:7.2f} mm   measured on a Type E; not printed on A or E",
        f"  drop below plate top  {spec.drop_below_plate_top_mm:7.2f} mm   18.89, printed on A and confirmed by calipers",
        f"    of which below the plate underside {spec.loop_drop_mm:5.2f} mm",
        f"  plate thickness       {spec.plate_thickness_mm:7.2f} mm   3, printed on A and E",
        f"  ear                   {float(spec.raw['envelope']['ear_width_mm']):7.2f} mm wide, "
        + f"{float(spec.raw['envelope']['ear_above_plate_mm']):.2f} mm proud   24 on A and E, and 21.19 - 18.89",
        f"    overall with the ear {spec.overall_with_ear_mm:6.2f} mm   21.19, Type H",
        "",
        "the loop: measured on the owned Type E",
        f"  mouth                 {spec.mouth_width_mm:7.2f} mm   calipers and Type A's section agree; half {spec.half_mouth_mm:.2f}",
        f"  post wall             {spec.post_wall_mm:7.2f} mm   from under the plate to the arch",
        f"  blade wall            {spec.blade_wall_mm:7.2f} mm   up through the plate's slot",
        f"  arch                  {spec.arch_wall_mm:7.2f} mm wall, semicircle at z {spec.arch_centre_z_mm:.2f}",
        f"  ledge                 {spec.lock_mm:.2f} mm out at z {spec.ledge_z_mm:.2f}, "
        + f"{spec.arm_depth_below_ledge_mm:.2f} mm of arm behind it",
        f"  blade tip             flush with the plate top, {spec.blade_tip_chamfer_mm:.2f} mm chamfer",
        "",
        "the joint it makes",
        f"  spread per leg        {spec.spread_mm:7.2f} mm   which is the same as the ledge's reach under the sheet",
        f"  sheet underside       {spec.ledge.drop_below_plate_mm:7.2f} mm below the plate underside",
        f"  actuator              {spec.raw['actuator']['insert']} {spec.raw['actuator']['thickness_mm']} mm, "
        + f"{spec.raw['actuator']['location']}",
        "",
        "bend tolerance",
        f"  flexure               {spec.flexure_length_mm:7.2f} mm developed, "
        + f"{spec.min_flexure_length_mm:.2f} mm needed",
        f"  wall that bends       {spec.bend_wall_mm:7.2f} mm",
        f"  strain                {spec.predicted_strain * 100:7.2f} %  "
        + f"({spec.predicted_stress_mpa:.1f} MPa, allowed {spec.allowable_strain * 100:.2f} %)",
        f"  opening force         {spec.opening_force_n:7.2f} N  (estimate)",
        "",
        "checks",
    ]
    width = max(len(c.name) for c in checks)
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        lines.append(f"  {mark} {c.name:<{width}}  {c.value:>12}  {c.limit:>18}  {c.note}")
    failed = [c for c in checks if not c.ok]
    lines.append("")
    lines.append(
        f"{len(checks) - len(failed)}/{len(checks)} checks pass"
        if not failed
        else f"{len(failed)} CHECK(S) FAILED"
    )

    verification = spec.raw.get("verification", {})
    callouts = verification.get("callouts", [])
    if callouts:
        lines += ["", "verified against the drawing set"]
        for c in callouts:
            value = c["value_mm"]
            shown = f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
            types = "/".join(c["types"])
            lines.append(f"  {shown:>22} {types:<14} {c['verdict']}")

    caliper = verification.get("caliper", [])
    if caliper:
        lines += ["", "checked against a Type E with calipers"]
        for c in caliper:
            value = c["value_mm"]
            if isinstance(value, (int, float)):
                shown = f"{value:.2f}"
            elif value is None:
                shown = "-"
            else:
                shown = str(value)
            lines.append(f"  {shown:>22} {'E':<14} {c['verdict']}")
        if verification.get("reference_type"):
            lines.append(f"  {'':>22} {'':<14} reference type {verification['reference_type']}")
        if verification.get("type_equivalence"):
            lines += ["", f"  type equivalence: {verification['type_equivalence']}"]
        policy = verification.get("fit_policy")
        if policy:
            lines += ["", f"  fit policy: {policy}"]

    mesh = verification.get("mesh_cross_check")
    if mesh:
        lines += ["", "cross-checked against enclosure_125b/dwg/125B_quickmount.stl"]
        for key, value in mesh["mesh_clip"].items():
            shown = f"{value:.2f}" if isinstance(value, float) else str(value)
            lines.append(f"  {key:<24} {shown}")
        for label in ("agreement", "disagreement"):
            for item in mesh.get(label, []):
                lines.append(f"  {label[:4]:<4} {item}")
        if mesh.get("verdict"):
            lines += ["", f"  mesh verdict: {mesh['verdict']}"]
        if mesh.get("also_noted"):
            lines += [f"  also noted: {mesh['also_noted']}"]
    return "\n".join(lines)


def summary(spec: Spec, checks: list[Check], stl: Path) -> dict:
    return {
        "id": spec.raw["id"],
        "stl": str(stl),
        "envelope_mm": {
            "width": spec.width_mm,
            "outer_width": spec.outer_width_mm,
            "height": spec.height_total_mm,
            "loop_drop": spec.loop_drop_mm,
        },
        "section_mm": {
            "mouth": spec.mouth_width_mm,
            "post_wall": spec.post_wall_mm,
            "blade_wall": spec.blade_wall_mm,
            "arch_wall": spec.arch_wall_mm,
            "arch_centre_z": spec.arch_centre_z_mm,
            "ledge": {
                "drop_below_plate": spec.ledge.drop_below_plate_mm,
                "protrusion": spec.ledge.protrusion_mm,
            },
        },
        "joint_mm": {
            "mouth": spec.mouth_width_mm,
            "blade_outer_width": spec.blade_outer_width_mm,
            "spread": spec.spread_mm,
            "ledge_reach": spec.lock_mm,
            "sheet_underside_below_plate": spec.ledge.drop_below_plate_mm,
        },
        "bend": {
            "flexure_length": spec.flexure_length_mm,
            "min_flexure_length": spec.min_flexure_length_mm,
            "strain_percent": spec.predicted_strain * 100.0,
            "allowable_strain_percent": spec.allowable_strain * 100.0,
            "stress_mpa": spec.predicted_stress_mpa,
            "opening_force_n": spec.opening_force_n,
        },
        "checks": [{"name": c.name, "value": c.value, "limit": c.limit, "ok": c.ok} for c in checks],
        "ok": all(c.ok for c in checks),
    }


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out", type=Path, default=DEFAULT_STL, help="STL to write")
    ap.add_argument("--step", type=Path, default=None, help="optional STEP alongside it")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    ap.add_argument("--tolerance", type=float, default=0.01, help="STL linear tolerance")
    args = ap.parse_args(argv)

    spec = load(args.config)
    part = build(spec)
    checks = validate(spec, part)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(part, str(args.out), tolerance=args.tolerance, angularTolerance=0.1)
    if args.step:
        args.step.parent.mkdir(parents=True, exist_ok=True)
        cq.exporters.export(part, str(args.step))

    if args.json:
        print(json.dumps(summary(spec, checks, args.out), indent=2))
    else:
        print(report(spec, checks, args.out))
        print(f"\nwrote {args.out}")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
