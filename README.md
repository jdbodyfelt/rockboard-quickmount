# rockboard-quickmount

Reverse engineering of Warwick's RockBoard QuickMount for custom pedal designs.

The goal is to extend the QuickMount system to pedals it does not cover: from a pedal name or a small JSON configuration to a printable, slot-compatible mounting plate.

## Layout

Every project — each pedal, board, enclosure, riser, and `commons` — uses the same four folders.

```text
<project>/
  cfg/    JSON configs. The geometric and input source of truth. All code reads from here.
  ref/    Raw material: scraped markdown, spec sheets, photos, drawings, reference meshes.
  src/    Source code, largely CADQuery.
  dwg/    Output drawings and meshes. What goes to the printer.
```

The first step of any job is always to build a configuration from the references, never to model from an image directly.

| Project | What it covers |
| --- | --- |
| `strymon_timeline_multiswitch/` | One joined mount: TimeLine on a riser, MultiSwitch flat |
| `digitech_whammy_v/` | Whammy V expression pedal |
| `line6_modeler/` | DL4 / FM4 / MM4 / DM4 / AM4 shared chassis |
| `pedal_riser/` | Second-tier riser; base inherited from the measured 125B mount |
| `enclosure_125b/` | Vertical 125B housing and the measured OEM plate |
| `rockboard_cinque_54/` | RockBoard Cinque 5.4 board: the slot grid substrate, and the whole board around it |
| `commons/` | Shared geometry and objects: the retainer, fastener presets, OEM type library |

`commons/` holds shared inputs (`cfg/fasteners.json`, `cfg/quickmount_types.json`, `cfg/pedalsafe_types.json`, `cfg/stepup_types.json`, `cfg/retainer.json`, `src/assets/fonts/`), the retainer generator (`src/retainer.py` → `dwg/retainer.stl`), and the OEM drawing library under `ref/`.

The library is Warwick's own drawings, scraped from the "Schematic Drawing" button on each product page and served from `https://cdn.rockboard.de/nos/data/erp/Artikell_PDF/PDF_Drawing/RockBoard/`:

| Folder | Source pages | Contents |
| --- | --- | --- |
| `ref/quickmounts/` | `/en/quickmounts/` | `QuickMount-Type<type>.pdf` for all 45 plate types in `cfg/quickmount_types.json`, a `-alt` second sheet for B1, K and L, and the QuickMount accessories |
| `ref/pedalsafes/` | `/en/pedalsafes/` | `PedalSafe-Type<type>.pdf` for every PedalSafe, with `-RBO` / `-UNI` suffixes where a type is published as both a plate and a universal baseplate |
| `ref/stepups/` | `/en/accessories/pedal-riser/`, `/en/accessories/second-tiers/` | `StepUp-1/2/3`, `PedalRiser`, `PedalRiser-L`, `SecondTier-Tier2S` |

The QuickMount drawing that each PedalSafe page also links is already in `ref/quickmounts/`, so it is not duplicated.

The three type catalogs carry geometry as well as names:

| Catalog | Covers | Geometry |
| --- | --- | --- |
| `cfg/quickmount_types.json` | 45 plate types | `dimensions_w_x_h_mm`, plus `mounting_hole_spacing_mm` where it is an exact pair and `mounting_hole_spacing_note` where it is ranged or asymmetric |
| `cfg/pedalsafe_types.json` | 55 cover types | `housing_dimensions_mm` of the pedal the cover is made for, `mounting_hole_spacing_published`, and `fits_quickmount_type` so plate geometry is referenced rather than copied |
| `cfg/stepup_types.json` | 6 riser units | `dimensions_mm` as length, width and height |

`geometry_source` on each entry says whether the numbers came off the product page (`product-spec`) or were read off the drawing outline (`drawing`); a drawing read carries no tolerance and wants calipers before it becomes a printed part.

## Running a generator

Each project's `src/` module reads its own config and writes into its own `dwg/`. A board project still uses two parts: the whole assembly, and the bare top plate that every mount has to fit.

```bash
python rockboard_cinque_54/src/cinque.py                    # board and top plate, STEP and STL
python rockboard_cinque_54/src/cinque.py --part top-plate --format step
python rockboard_cinque_54/src/cinque.py --check            # derived slot field, no geometry
python commons/src/retainer.py                              # the retainer, dwg/retainer.stl
python commons/src/retainer.py --json                       # machine-readable summary and checks
```

The retainer exits non-zero if any of its 20 checks fail, so it can gate a build.

CADQuery lives in the repo's `.venv`:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe cadquery
```

## Config conventions

- Units are part of the field name: `_mm`, `_g`, `_deg`, `_percent`.
- Paths in a config are relative to that project's own folder, so a pedal reaching into `commons/` writes `../commons/...`.
- Unknown values are `null`, never a guessed number. A null blocks generation on purpose.
- Fasteners are referenced by id from `commons/cfg/fasteners.json` rather than restated per pedal, so a corrected clearance applies everywhere at once.
- Datum is the pedal's bottom-face centre, +X along width, +Y along depth, +Z away from the pedal, viewed from below. A board project states its own datum in a `datum` block instead, because the plate sits on top of it.
- Every dimension block carries `provenance` with a confidence level and its source:

| Level | Meaning |
| --- | --- |
| 0 | Unknown |
| 1 | Design intent |
| 2 | Secondhand — vendor page, spec markdown, catalogue |
| 3 | Official drawing or published dimension |
| 4 | Measured by the owner |

Anything at level 2 or below is a candidate for calipers before it becomes a printed part.
