# Rendering pipeline

Goal: deterministic, headless generation of printable STLs from declarative inputs, with enough validation that a bad part cannot be exported silently.

## 1. Requirements

| Requirement | Consequence |
| --- | --- |
| Reproducible | Same inputs and tool versions produce the same solid; record both in a manifest |
| Parametric | Board, pedal, printer, and tolerance are parameters, not edits to source |
| Headless | Runs in CI and in batch; no GUI steps |
| Reviewable | Emit STEP alongside STL so a human can inspect and section the model |
| Validated | Watertight, single solid, minimum wall thickness, hole positions checked |
| Batch-friendly | Many pedals, one manifest, parallel workers |
| Traceable | Every output names the inputs and the data confidence behind them |

## 2. Tool choice

| Option | Model | Licence | Strengths | Weaknesses |
| --- | --- | --- | --- | --- |
| **build123d** | B-rep (OCCT) | Apache-2.0 | Python-native, expressive sketches, STEP/STL export, active project | OCCT dependency size; tessellation settings matter |
| CadQuery | B-rep (OCCT) | Apache-2.0 | Mature, large community, good selectors | Fluent API less Pythonic for complex sketches |
| OpenSCAD | CSG | GPL-2.0 | Tiny dependency, trivial CI, text-diffable models | Weak at fillets and organic shapes; slow for complex parts; GPL implications for distribution |
| trimesh | Mesh | MIT | Fast checks, boolean via manifold3d, excellent for validation | Not a design kernel; fragile booleans |
| manifold3d | Mesh | Apache-2.0 | Robust booleans, fast | Mesh-only, no parametric sketches |

**Recommendation:** build123d as the design kernel, with trimesh for validation. Keep OpenSCAD as a fallback only if build123d cannot be installed in the target environment.

Rationale: the design is dominated by a small number of extruded 2D profiles (slot tab, keeper, plate outline) with fillets and countersinks. B-rep handles those cleanly and exports STEP for review. Mesh booleans are too fragile for repeated hole/boss operations, and OpenSCAD's boolean engine struggles with the fillets we will need on load-bearing tabs.

Pin the exact version in the lock file. OCCT tessellation and boolean results can change between releases, so version drift is a reproducibility bug.

## 3. Pipeline

```
input YAML ──► schema validation ──► resolved parameter set
                                            │
                                            ▼
                                  derived geometry (datums,
                                  offsets, clearances)
                                            │
                                            ▼
                             2D profiles: plate outline, slot tab,
                             keeper, holes, pockets
                                            │
                                            ▼
                             solids: extrude, fuse, cut, fillet
                                            │
                                            ▼
                             solid checks (see §4)
                                            │
                    ┌───────────────────────┴────────────────────┐
                    ▼                                            ▼
             STEP (review)                              STL (print)
                    └───────────────────────┬────────────────────┘
                                            ▼
                                   manifest + build report
```

### 3.1 Parameter resolution

- Merge pedal + board + printer/material + tolerance profiles.
- Compute derived values once and log them: screw boss height, tab length, keeper preload, plate thickness.
- Fail if a required value is missing or below its confidence gate ([pedal-data.md](pedal-data.md#4-confidence-model)).
- Quantise values to 0.01 mm before building so floating-point noise cannot change a design.

### 3.2 Modelling conventions

- Units: millimetres throughout; no unit conversion inside the modeller.
- One function per feature, each returning a named solid; compose explicitly rather than with long fluent chains.
- Fillets and chamfers only after all cuts, so edges are well-defined.
- Keep the slot profile in a single module shared by the coupon generator and the plate generator. Coupons and production parts must never diverge.

### 3.3 Export

| Output | Settings |
| --- | --- |
| STL | Binary; linear deflection 0.05 mm; angular deflection 10° |
| STEP | AP214; include a title with the pedal and board IDs |
| Manifest | JSON with input hash, resolved parameters, tool versions, git commit, output hashes |

Expose tessellation tolerances as parameters, but keep the defaults above. Coarser STLs hide thin-wall problems; finer ones bloat files.

## 4. Validation gates

Run before export; any failure aborts the build.

| Gate | Check | Threshold |
| --- | --- | --- |
| Schema | Input validates against JSON Schema | Error-free |
| Solid count | Exactly one solid after fusion | 1 |
| Watertight | Mesh is closed and manifold | No boundary edges |
| Volume | Positive and within an expected range for the envelope | ±20 % of estimate |
| Bounding box | Matches the pedal footprint plus margins | ±0.5 mm |
| Wall thickness | Minimum wall at least 3 perimeters | ≥ 1.2 mm at 0.4 mm nozzle |
| Feature size | Smallest positive feature printable | ≥ 0.8 mm |
| Hole placement | Hole centres match the input within tolerance | ±0.05 mm |
| Interference | Tab/keeper do not intersect the slot envelope at nominal clearance | Zero interference |
| Clearance | Tab fits the slot at the worst-case tolerance | Positive clearance |
| Overhang | Report faces above the support threshold | Informational |

The interference check deserves emphasis: build the board slot as a **negative volume** and assert a minimum gap around the tab and keeper for every variant in the tolerance profile. This catches a class of error that a visual check misses.

## 5. Print orientation

Two candidate orientations must be tested in Phase 1:

| Orientation | Pros | Cons |
| --- | --- | --- |
| Plate face down, tabs rising | No supports on the pedal face; clean cosmetic surface | Bending load on tabs crosses layer lines (weak) |
| Plate on edge, tabs horizontal | Layer lines perpendicular to tab bending (strong) | Large support footprint; bed adhesion risk for tall thin parts |
| Tab face down, plate vertical (hybrid) | Tab stronger; plate still manageable | More support, longer print |

Decision rule: print the same coupon in each orientation, then run the pull-off and creep tests. Adopt the orientation that meets retention with the least support and post-processing. Record the result as the default `print_orientation` in the printer profile.

Kea Modelling's instant-quote flow may choose the orientation itself. Confirm this in the vendor consultation; if the orientation cannot be controlled, encode it in the STL (submit a pre-rotated model) and record the intended orientation in the manifest and order note.

## 6. Material and vendor profiles

Kea Modelling offers **PLA and PETG only** ([manufacturing.md](manufacturing.md)). The profile set reflects that constraint.

| Profile | Material | Status | Use |
| --- | --- | --- | --- |
| `kea_petg` | PETG | **Default, pending coupon validation** | All functional plates and coupons |
| `kea_pla` | PLA | Prototype only | Fit checks that never see service or heat |
| `inhouse_asa` | ASA | Not available from Kea; optional future in-house | Fallback if PETG creep fails at 70 °C |
| `inhouse_pa_cf` | PA-CF | Not available from Kea; optional future in-house | Stiffest fallback; abrasive, needs hardened nozzle |

The vendor's layer height, wall count, and infill defaults are unpublished; the `kea_petg` profile starts with the assumptions in [manufacturing.md §3](manufacturing.md#3-design-rules-for-fdm-in-petg) and is corrected after the calibration coupon.

Each profile contains: vendor name, shrinkage compensation (X/Y and Z), first-layer expansion compensation, clearance offsets, and the validated print orientation. Calibrate per vendor and material; do not copy values between printers or spools. A profile with `validated: false` raises a warning on every export.

## 7. Reproducibility

- Lock file for Python dependencies; record `build123d`, `OCCT`, and `trimesh` versions in the manifest.
- Do not use timestamps or random UUIDs inside the model.
- Output names are deterministic: `{pedal_id}__{board_profile}__{printer_profile}__r{revision}.stl`, where `revision` is the content hash of the resolved parameters, truncated to 8 hex characters.
- Store the manifest next to the STL. A design is reproducible only if the manifest and the input records are both available.

## 8. Batch generation

Input: a manifest listing pedal IDs and the profiles to apply.

```
qm batch pedals.yaml --board cinque-5.2 --printer kea_petg --out build/
```

Behaviour:

- Parallelise across pedals with a process pool; one failing design must not abort the batch.
- Produce a summary table: pedal, status, output file, warnings, confidence minimum.
- Reuse resolved OEM type patterns across pedals to keep runs fast.
- Emit a machine-readable `build/report.json` for CI and a human-readable `build/report.md`.
- Split the output into vendor orders: at most 10 STL files and 500 g per part for Kea's instant quote. Emit an `orders/` folder with one subfolder per order and a packing list.

## 9. CI checks

- `pytest` for schema validation, parameter resolution, and feature-level unit tests.
- Geometry regression: compare volume, bounding box, and hole coordinates against golden values with tolerances (do not compare file hashes; they are brittle across OCCT versions).
- Manifold check on every exported STL.
- Lint and type-check the Python package.
- A nightly job that regenerates the example set and fails on drift.

## 10. Repository layout

```
quickmount/
  __init__.py
  cli.py                 # generate, batch, validate, lookup
  params/
    __init__.py
    schema.py            # dataclasses + JSON Schema
    resolve.py           # merge profiles, derive dimensions
  cad/
    slot_profile.py      # the single source of truth for the board interface
    plate.py             # pedal interface and outline
    features.py          # holes, bosses, pockets, fillets
    export.py            # STEP/STL + manifest
  catalog/               # pedal YAML, board profiles, type library
  lookup/                # identity resolution and source fetchers
  validate/              # geometric checks
tests/
```

The slot profile module is deliberately small and heavily tested. It is the part that must match the physical board.

## 11. Dependencies

- Python 3.12+
- `build123d` (Apache-2.0), `trimesh` (MIT), `manifold3d` (Apache-2.0)
- `pydantic` or `jsonschema` for validation
- `typer` or `click` for the CLI
- `pytest`, `ruff`, `mypy` for development
- `pyyaml` for the catalog

## 12. Open questions

1. Does build123d's OCCT boolean remain stable enough for a CI golden test, or do we need to pin OCCT separately?
2. Is a single-piece printed PETG keeper sufficient, or does the design need a captured spring or screw clamp?
3. Which print orientation wins the pull-off and creep tests?
4. Can Kea Modelling accept a specified orientation, or must we submit pre-rotated STLs?
5. What layer height, wall count, and infill does Kea use, and can they be changed? (Blocks a truly validated profile.)
6. Multi-material is not available from Kea; is a soft-pad variant worth supporting in-house?

## Sources

- build123d: <https://github.com/gumyr/build123d>
- CadQuery: <https://github.com/CadQuery/cadquery>
- OpenSCAD: <https://openscad.org/>
- trimesh: <https://github.com/mikedh/trimesh>
- manifold: <https://github.com/elalish/manifold>
- Kea Modelling: [manufacturing.md](manufacturing.md)
