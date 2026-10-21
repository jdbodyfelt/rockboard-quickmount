# Input schema

Proposed YAML formats for pedals, board profiles, printer profiles, and batch manifests. Files live in `quickmount/catalog/` and user projects, and are validated against a JSON Schema generated from the same dataclasses.

Status: **design proposal**. Nothing here is implemented yet; the schema will be finalised during Phase 2.

## 1. Conventions

- Units are part of the field name: `_mm`, `_g`, `_deg`, `_percent`.
- The datum is the pedal's bottom-face centre, +X along width, +Y along depth, +Z away from the pedal, viewed from below. Hole coordinates are relative to that origin.
- `id` values are lowercase snake case and stable forever; they are used in filenames and manifests.
- Every value block carries `provenance` with a confidence level (0–4) and a source.
- Unknown values are `null`, never a guessed number.

## 2. Pedal

```yaml
schema_version: 1
id: example_1590b
brand: Example
model: Example Drive
aliases: ["Example Drive v2"]
housing_family: 1590b          # optional
physical:
  width_mm: 60.0
  depth_mm: 112.0
  height_mm: 31.0
  weight_g: 300
mounting:
  quickmount_type: null        # e.g. "E" when the OEM type is known
  holes:
    - {x_mm: -20.0, y_mm: 25.0, thread: M3, depth_mm: 8.0, recessed_mm: 0.0}
    - {x_mm: 20.0, y_mm: 25.0, thread: M3, depth_mm: 8.0, recessed_mm: 0.0}
  feet:
    present: false
    positions: []
  battery_door:
    present: true
    x_mm: 0.0
    y_mm: -10.0
    width_mm: 30.0
    depth_mm: 45.0
provenance:
  physical: {level: 4, source: "calipers 2026-10-21", retrieved: 2026-10-21}
  mounting: {level: 4, source: "calipers 2026-10-21", retrieved: 2026-10-21}
```

> The values above are **illustrative**, not a real pedal. Do not generate a design from them.

### 2.1 Field rules

| Field | Required | Rule |
| --- | --- | --- |
| `id` | Yes | `^[a-z0-9]+(_[a-z0-9]+)*$` |
| `brand`, `model` | Yes | Non-empty strings |
| `physical.width_mm`, `depth_mm`, `height_mm` | Yes | > 0; dimension confidence ≥ 2 |
| `physical.weight_g` | Yes | > 0; used for retention assumptions |
| `mounting.holes` | Yes | 1–6 entries; hole confidence ≥ 3 |
| `holes[].thread` | Yes | Enum of supported threads; unknown requires explicit user override |
| `holes[].depth_mm` | Yes | > 0 and ≤ pedal height |
| `mounting.quickmount_type` | No | If present, the type library pattern may replace `holes` after confirmation |
| `feet.present` | Yes | Boolean |
| `battery_door` | No | Required if the plate would span the door |

## 3. Board profile

```yaml
schema_version: 1
id: cinque_5_2
family: Cinque
model: Cinque 5.2
envelope:
  width_mm: 622.0
  depth_mm: 424.0
slot:
  width_mm: null              # Open — measure
  length_mm: null
  end_radius_mm: null
  pitch_x_mm: null
  pitch_y_mm: null
  rib_width_mm: null
  edge_margin_x_mm: null
  edge_margin_y_mm: null
sheet:
  thickness_mm: null
  powder_coat_mm: null
  mounting_angle_deg: null
  under_sheet_clearance_mm: null
mod_slots:
  present: true
  width_mm: null
  length_mm: null
  pitch_x_mm: null
provenance:
  envelope: {level: 3, source: "https://www.rockboard.de/downloads/RockBoard_Catalog.pdf p.6", retrieved: 2026-10-21}
  slot: {level: 0, source: null, retrieved: null}
```

A board profile with any `null` slot or sheet value is **incomplete** and cannot be used for generation. This is intentional: it prevents an unmeasured board from silently producing parts.

## 4. Printer and tolerance profile

```yaml
schema_version: 1
id: petg_04_plate_face_down
material: PETG
nozzle_mm: 0.4
layer_mm: 0.20
walls: 4
infill_percent: 40
print_orientation: plate_face_down
clearance:
  tab_side_mm: 0.30
  tab_end_mm: 0.40
  keeper_interference_mm: 0.20
  screw_clearance_m3_mm: 3.40
  screw_clearance_m4_mm: 4.50
compensation:
  shrink_xy_percent: 0.30
  shrink_z_percent: 0.10
  elephant_foot_mm: 0.15
tessellation:
  linear_mm: 0.05
  angular_deg: 10.0
```

Clearance values are validated by coupons ([geometry-capture.md](geometry-capture.md#6-fit-coupons)); a profile without a coupon result is marked `validated: false` and the CLI warns.

## 5. QuickMount type library

```yaml
schema_version: 1
type: E
product_no: RBO B QM T E
compatibility: ["BOSS compact series"]
hole_pattern:
  - {x_mm: null, y_mm: null, thread: null}
plate:
  thickness_mm: null
  tab_width_mm: null
  keeper_height_mm: null
provenance:
  compatibility: {level: 3, source: "RockBoard catalogue p.20", retrieved: 2026-10-21}
  hole_pattern: {level: 0, source: null, retrieved: null}
```

This library is the bridge between the OEM compatibility lists and our generator (see [pedal-data.md](pedal-data.md#3-the-oem-type-library-shortcut)).

## 6. Batch manifest

```yaml
schema_version: 1
defaults:
  board: cinque_5_2
  printer: petg_04_plate_face_down
items:
  - pedal: boss_ds_1
  - pedal: wampler_tumnus_deluxe
    printer: asa_04_plate_face_down
  - pedal: example_1590b
    board: quad_4_2
```

Rules:

- An item may override `board` and `printer`.
- Duplicate `pedal` entries with different boards are allowed and produce separate outputs.
- A missing pedal record is an error for that item, not for the batch.

## 7. Validation summary

| Stage | Check | On failure |
| --- | --- | --- |
| Parse | YAML well-formed, schema version supported | Error |
| Schema | Types, ranges, required fields, enum values | Error |
| Completeness | All required values non-null | Error with the missing field list |
| Confidence | Required fields meet the gate | Error; prompt for the missing data |
| Consistency | Screw depth ≤ height; holes inside footprint; feet inside footprint | Error |
| Physical | Board profile complete; slot clearance positive | Error |
| Profile | Printer profile validated by coupons | Warning (or error with `--strict`) |

## 8. CLI sketch

```text
qm generate --pedal boss_ds_1 --board cinque_5_2 --printer petg --out build/
qm batch pedals.yaml --out build/
qm validate --board cinque_5_2
qm coupon --board cinque_5_2 --printer petg --out build/coupons/
qm lookup "Wampler Tumnus Deluxe"          # resolve or prompt for missing data
qm lookup "Wampler Tumnus Deluxe" --photo pedal.jpg
```

Exit codes: `0` success, `1` validation failure, `2` missing data, `3` internal error. CI relies on these.

## 9. Open questions

1. Should hole coordinates be relative to the pedal centre or to a corner? Centre is symmetric and less error-prone when a user measures spacing only.
2. Do we need a separate `spacer` block for feet replacement or riser adapters?
3. Should the board profile carry a measured "slot map" (explicit slot positions) instead of a regular pitch, in case the grid is irregular?
4. How do we represent slotted holes on OEM type plates (round pattern plus a tolerance range, or explicit slot geometry)?
