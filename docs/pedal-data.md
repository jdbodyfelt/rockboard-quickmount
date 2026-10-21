# Pedal data and lookup

The hardest input is not the CAD; it is knowing the pedal's geometry well enough to place screw holes. This document defines what we need, where it can come from, and how much we trust each value.

## 1. Required fields

A design can only be generated when the fields marked **required** are known.

| Field | Required | Why |
| --- | --- | --- |
| Brand and model | Yes | Identity and compatibility lookup |
| Housing family (if known) | Helpful | Inherits plate type and typical screw pattern |
| Width, depth, height | Yes | Plate footprint and clearance checks |
| Weight | Yes | Retention and creep assumptions |
| Screw holes: count | Yes | Determines the plate interface |
| Screw holes: X/Y offsets | Yes | Hole placement |
| Screw holes: thread | Yes | Clearance hole and screw BOM |
| Screw holes: usable depth | Yes | Prevents over-driving |
| Rubber feet: presence and position | Yes | Pockets or reliefs |
| Battery door: presence and position | Yes | Cut-outs |
| QuickMount type (OEM compatibility) | Helpful | Shortcut to a verified hole pattern |
| Source and confidence per field | Yes | Traceability |

## 2. Source hierarchy

Ranked from most to least trustworthy. Record the level with every value.

| Level | Source | Notes |
| --- | --- | --- |
| L0 | Manufacturer drawing, CAD, or dimensioned PDF | Best; cite the file and page |
| L1 | Manufacturer specification text (manual, product page) | Dimensions usually available; screw offsets rarely |
| L2 | Authorised retailer or distributor specification | Good for dimensions; occasionally screw data |
| L3 | Community database with its own sources | Verify the cited source, not the aggregator |
| L4 | Measured by the user or by us, with calibration | Strongest for screw offsets; record method |
| L5 | Inferred from housing family or OEM plate type | Acceptable with explicit confirmation and a fit test |

**Never** accept a value without a level. A generated design records the level of every input.

Existing resources worth evaluating:

- **RockBoard PedalPedia and QuickMount Finder** (<https://www.rockboard.de/en/pedalPedia/>, <https://www.rockboard.de/en/quickMountFinder/>). These are the vendor's own pedal catalogue and compatibility tool. PedalPedia appears to be a JavaScript application; check its terms and any public API before automating access.
- **RockBoard catalogue** QuickMount compatibility lists (Official, but coarse).
- **Manufacturer spec pages**, especially those with dimensioned drawings (BOSS, Strymon, Eventide, Universal Audio, Lehle, TC Electronic publish reliable figures).
- **Retailer specifications** (Thomann, Sweetwater, Andertons) for dimensions.
- **Community datasets**, for example `emilwu/Pedal-Research`, which stores per-pedal YAML with dimensions and source annotations. That repository has no declared licence, so it may be used as a **reference and source of leads only**; do not copy its data into this repository.
- **Effects Database / Equipboard / forums** for corroboration.

Reject or quarantine any source that forbids automated access. Cache fetched pages, rate-limit, and identify the client.

## 3. The OEM type library shortcut

This is the highest-leverage idea in the project.

RockBoard publishes, for each QuickMount type, the pedals it fits. A plate type has one screw-hole pattern (possibly slotted) that is known to work with every pedal on that list. Therefore:

1. **Measure or obtain the hole pattern of each OEM type once.** That is ~40 patterns, not thousands of pedals.
2. **Map brand/model → OEM type** using RockBoard's published compatibility lists (Official).
3. **Generate** a plate that reuses the verified pattern, adding only pedal-specific features (foot pockets, battery cut-outs, overhang support).

Consequences:

- For any pedal with an official QuickMount type, the screw geometry is **already validated by the vendor**. We do not need to discover screw offsets at all.
- The lookup problem collapses to identity resolution and type mapping.
- Pedals without an official type fall back to measurement or housing-family inference.

Open questions the measurements must answer: are the type's holes round or slotted, what tolerance range do they cover, and does the plate rely on the pedal's own screws for clamping or only for location?

## 4. Confidence model

Store confidence **per field**, not per pedal.

| Score | Meaning | May be used for generation? |
| --- | --- | --- |
| 0 | Unknown | No |
| 1 | Single unverified community claim | No |
| 2 | Corroborated by two independent sources, or one retailer spec | Dimensions only |
| 3 | Manufacturer text or OEM compatibility mapping | Yes, with fit test |
| 4 | Manufacturer drawing or our own calibrated measurement | Yes |

Generation gate:

- every **required** field must be ≥ 2;
- every screw-hole field must be ≥ 3;
- if any required field is below the gate, the tool must ask for the missing data instead of guessing.

## 5. Lookup pipeline

Staged resolver, cheapest and most reliable first. Each stage either returns a complete, gated record or hands off to the next.

```
user input ("Wampler Tumnus Deluxe")
        │
        ▼
1. Normalise and resolve identity  ──► ambiguous? ask user
        │
        ▼
2. Local catalogue (git-tracked YAML/SQLite)
        │ miss
        ▼
3. OEM compatibility map (brand/model → QuickMount type)  ──► type library
        │ miss
        ▼
4. Manufacturer site (sitemap/search → product page → spec/drawing)
        │ miss
        ▼
5. Retailer / distributor specifications
        │ miss
        ▼
6. General web search (cited snippets only)
        │ miss
        ▼
7. Ask the user for measurements (worksheet or calibrated photo)
        │
        ▼
8. Validate, score, store with provenance
```

Rules for stages 4–6:

- Extraction is **schema-constrained**: the extractor may only fill the fields in the schema and must return the supporting quote and URL for each value.
- An LLM may normalise, convert units, and extract; it may **not** infer a number that is not present in a retrieved document. A missing value stays missing.
- Cross-check dimensions against a plausibility range for the housing family (for example, a "compact" pedal is not 300 mm wide).
- Cache every fetched document with its URL, fetch time, and hash so a design can be reproduced.
- Respect `robots.txt` and site terms; do not bypass access controls.

## 6. User measurement workflow

When automation fails, the user must be able to supply accurate data without a caliper.

**Calibrated photo method (preferred):**

1. Provide a printable calibration card (a page with an accurate ruler and four fiducial markers).
2. User places the pedal face-down on the card, aligned with the ruler, and photographs it from directly above.
3. Tool rectifies the image, detects the enclosure outline and screw holes, and converts pixels to millimetres.
4. Tool shows the detected geometry overlaid on the photo for the user to confirm or correct.

**Worksheet method (fallback):**

- Printable 1:1 grid; user marks hole centres and photographs or scans it.
- Or a short form: width, depth, hole spacing X/Y, thread, depth.

Both methods record an estimated error (typically ±0.3 mm for photos, ±0.1 mm for calipers) that feeds the tolerance profile.

## 7. Data model

One YAML file per pedal, human-readable and reviewable in a pull request. See [input-schema.md](input-schema.md) for the full schema. Minimum shape:

```yaml
id: wampler_tumnus_deluxe
brand: Wampler
model: Tumnus Deluxe
aliases: ["Tumnus Deluxe"]
housing_family: compact_125b
physical:
  width_mm: 73
  depth_mm: 116
  height_mm: 56
  weight_g: 400
mounting:
  quickmount_type: null
  holes:
    - {x_mm: -31.5, y_mm: 0, thread: M3, depth_mm: 9}
  feet:
    present: false
provenance:
  dimensions: {level: 2, source: "https://example.com/spec", retrieved: 2026-10-21}
  holes: {level: 4, source: "user measurement 2026-10-21", retrieved: 2026-10-21}
```

Hole coordinates use the datum defined in [rockboard-system.md](rockboard-system.md#4-mounting-plane-and-coordinate-system): origin at the pedal's bottom-face centre, +X along width, +Y along depth, viewed from below. State the viewing convention in the file header.

## 8. Data quality rules

1. Units are always explicit in the field name (`_mm`, `_g`).
2. Dates are ISO 8601.
3. A pedal with conflicting sources keeps both entries and a `disputed: true` flag.
4. Housing-family values are never silently copied into a pedal record; they must be marked L5.
5. Deleting data requires a note explaining why; history lives in git.
6. Never commit scraped page dumps. Commit only extracted facts, quotes, and URLs.

## 9. Open questions

1. Does RockBoard PedalPedia expose a public API or export, and do its terms permit use?
2. Are QuickMount type holes round or slotted, and what range do they cover?
3. How consistent are screw patterns within a housing family across brands?
4. Which thread sizes dominate? (Sample the top 50 pedals.)
5. Can a photo-based measurement reach the ±0.3 mm needed for screw bosses?

## Sources

- RockBoard QuickMount Finder: <https://www.rockboard.de/en/quickMountFinder/>
- RockBoard PedalPedia: <https://www.rockboard.de/en/pedalPedia/>
- RockBoard catalogue: <https://www.rockboard.de/downloads/RockBoard_Catalog.pdf>
- Pedal-Research dataset (reference only, no declared licence): <https://github.com/emilwu/Pedal-Research>
