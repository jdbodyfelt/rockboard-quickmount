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
| `rockboard_cinque_54/` | RockBoard Cinque 5.4 board profile (slot grid) |
| `commons/` | Shared geometry and objects: clips, fastener presets, OEM type library |

`commons/` holds two kinds of shared material: shared inputs (`cfg/fasteners.json`, `cfg/quickmount_types.json`, `src/assets/fonts/`) and the OEM blueprint set under `ref/quickmount_drawings/`.

## Config conventions

- Units are part of the field name: `_mm`, `_g`, `_deg`, `_percent`.
- Paths in a config are relative to that project's own folder, so a pedal reaching into `commons/` writes `../commons/...`.
- Unknown values are `null`, never a guessed number. A null blocks generation on purpose.
- Fasteners are referenced by id from `commons/cfg/fasteners.json` rather than restated per pedal, so a corrected clearance applies everywhere at once.
- Datum is the pedal's bottom-face centre, +X along width, +Y along depth, +Z away from the pedal, viewed from below.
- Every dimension block carries `provenance` with a confidence level and its source:

| Level | Meaning |
| --- | --- |
| 0 | Unknown |
| 1 | Design intent |
| 2 | Secondhand — vendor page, spec markdown, catalogue |
| 3 | Official drawing or published dimension |
| 4 | Measured by the owner |

Anything at level 2 or below is a candidate for calipers before it becomes a printed part.
