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
| `strymon_timeline_multiswitch/` | One joined mount: TimeLine on a riser, original three-switch MultiSwitch (not MultiSwitch Plus) flat. The TimeLine half is the Type J1 plate, reproduced from Warwick's drawing |
| `digitech_whammy_v/` | Whammy V expression pedal - being rebuilt from measured dimensions: start at `metrics.html`, the measurement runbook |
| `line6_modeler/` | DL4 / FM4 / MM4 / DM4 / AM4 shared chassis |
| `stepup_risers/` | Printed step-up risers in the Step Up's form - front leg, sloped deck, rear leg - with the board's slot field on the deck so QuickMount plates drop on, and a 3 mm plate with integral clips underneath so the riser clips to the board. `single_125b` is the riser for one 125B, built from the Type B1 plate instead: `single_125b.py` is its clip-free base plate. `pedal_riser.py` reproduces the reference product itself - 135.0 x 76.0 x 41.0 of 2.0 steel sheet on four rubber pads - so the printed parts have the real thing to measure against |
| `enclosure_125b/` | Vertical 125B housing and the Type B1 plate, reproduced from Warwick's own drawing |
| `rockboard_cinque_54/` | RockBoard Cinque 5.4 board: the slot grid substrate, and the whole board around it |
| `commons/` | Shared geometry and objects: the retainer, fastener presets, OEM type library |

`commons/` holds shared inputs (`cfg/fasteners.json`, `cfg/quickmount_types.json`, `cfg/pedalsafe_types.json`, `cfg/stepup_types.json`, `cfg/retainer.json`, `src/assets/fonts/`), the retainer generator (`src/retainer.py` → `dwg/retainer.stl`), and the OEM drawing library under `ref/`.

The library is Warwick's own drawings, scraped from the "Schematic Drawing" button on each product page and served from `https://cdn.rockboard.de/nos/data/erp/Artikell_PDF/PDF_Drawing/RockBoard/`:

| Folder | Source pages | Contents |
| --- | --- | --- |
| `ref/quickmounts/` | `/en/quickmounts/` | `QuickMount-Type<type>.pdf` for all 45 plate types in `cfg/quickmount_types.json`, a `-alt` second sheet for B1, K and L, and the QuickMount accessories |
| `ref/pedalsafes/` | `/en/pedalsafes/` | `PedalSafe-Type<type>.pdf` for every PedalSafe, with `-RBO` / `-UNI` suffixes where a type is published as both a plate and a universal baseplate |
| `ref/stepups/` | `/en/accessories/pedal-riser/`, `/en/accessories/second-tiers/` | `StepUp-1/2/3`, `PedalRiser`, `PedalRiser-L`, `SecondTier-Tier2S`; read in `stepup_risers/ref/stepup_geometry_review.md` |

The QuickMount drawing that each PedalSafe page also links is already in `ref/quickmounts/`, so it is not duplicated.

The three type catalogs carry geometry as well as names:

| Catalog | Covers | Geometry |
| --- | --- | --- |
| `cfg/quickmount_types.json` | 45 plate types | `dimensions_w_x_h_mm`, plus `mounting_hole_spacing_mm` where it is an exact pair and `mounting_hole_spacing_note` where it is ranged or asymmetric |
| `cfg/pedalsafe_types.json` | 55 cover types | `housing_dimensions_mm` of the pedal the cover is made for, `mounting_hole_spacing_published`, and `fits_quickmount_type` so plate geometry is referenced rather than copied |
| `cfg/stepup_types.json` | 6 riser units | `dimensions_mm` as length, width and height, plus `top.slotted` so it is explicit which of them can carry a QuickMount plate |

`geometry_source` on each entry says whether the numbers came off the product page (`product-spec`) or were read off the drawing outline (`drawing`); a drawing read carries no tolerance and wants calipers before it becomes a printed part.

## Running a generator

Each project's `src/` module reads its own config and writes into its own `dwg/`. A board project still uses two parts: the whole assembly, and the bare top plate that every mount has to fit.

```bash
python enclosure_125b/src/quickmount_125b.py                # B1 plate and its bare base, STL and STEP
python enclosure_125b/src/quickmount_125b.py --part base    # only the plate, no clips
python enclosure_125b/src/quickmount_125b.py --part clip --clip-variant oem   # refresh ref/125B_oem_clip_fingers
python strymon_timeline_multiswitch/src/quickmount_j1.py    # J1 plate and its bare base, STL and STEP
python strymon_timeline_multiswitch/src/quickmount_j1.py --part base   # only the plate, no clips
python strymon_timeline_multiswitch/src/coplanar_riser.py   # export separate TimeLine step and two-clip MultiSwitch plate
python strymon_timeline_multiswitch/src/coplanar_riser.py --part timeline    # export only the TimeLine step
python strymon_timeline_multiswitch/src/coplanar_riser.py --part multiswitch # export only the MultiSwitch plate
python strymon_timeline_multiswitch/src/coplanar_riser.py --check  # validate both units, clips, hole patterns, and cable tunnel
python digitech_whammy_v/src/make_runbook.py                # metrics.html: the measurement runbook
python digitech_whammy_v/src/prepare_refs.py                # ref/clean: balanced, cropped, rectified stills
# superseded until the runbook comes back filled; these need cfg/digitech_whammy_v.json
python digitech_whammy_v/src/quickmount_whammy_v.py         # basket, ring, set, and both check models
python digitech_whammy_v/src/pedal_sheet.py                 # ref/pedal_sheet.png, ref/mount_sheet.png, renders
python rockboard_cinque_54/src/cinque.py                    # board and top plate, STEP and STL
python rockboard_cinque_54/src/cinque.py --part top-plate --format step
python rockboard_cinque_54/src/cinque.py --check            # derived slot field, no geometry
python stepup_risers/src/stepup_riser.py --list             # the riser configs
python stepup_risers/src/stepup_riser.py --config riser_two_125b            # STEP and STL
python stepup_risers/src/stepup_riser.py --config riser_line6_modeler
python stepup_risers/src/stepup_riser.py --config riser_two_125b --check    # derived field and checks
python stepup_risers/src/single_125b.py                     # single_125b base plate, STL and STEP
python stepup_risers/src/single_125b.py --check             # the base's checks, no geometry
python stepup_risers/src/single_125b_riser.py               # the plate tipped onto the PedalRiser deck, STL and STEP
python stepup_risers/src/single_125b_riser.py --check       # the placement's checks, no geometry
python stepup_risers/src/riser_check.py                    # riser-check.stl: the riser beside the PedalRiser
python stepup_risers/src/riser_check.py --check            # the comparison's checks, no geometry
python stepup_risers/src/pedal_riser.py                     # the reference PedalRiser, STL and STEP
python stepup_risers/src/pedal_riser.py --check             # the reference's checks, no geometry
stepup_risers/brainstorm.md                                # attachment alternatives and next design pass
python stepup_risers/src/dual_125b_riser.py                # left/right dovetail plates and dual board-clipping wedge
python stepup_risers/src/dual_125b_riser.py --check        # watertight and layout checks, no exports
python commons/src/retainer.py                              # the retainer, dwg/retainer.stl
python commons/src/retainer.py --json                       # machine-readable summary and checks
```

Both generators exit non-zero if a check fails, so either can gate a build: the retainer runs 20 checks, the 125B plate 38, the J1 plate 43, each riser 14, the `single_125b` base 24, the tube-free `single_125b_riser` placement 11, the `riser_check` layout 4, and the PedalRiser reference 33.

`stepup_risers/` is also the written review of the reference sheets: `ref/stepup_geometry_review.md` records what the Step Up kits and the PedalRiser family actually are, and why the printed riser takes its top from one and its envelope from the other.

`prepare_refs.py` is a reference tool rather than a build step. It needs Pillow and numpy
(scipy only for the plan-view feature read-out) and writes only into `ref/clean/`.

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
