# Geometry capture and metrology

Purpose: turn the Open parameters in [rockboard-system.md](rockboard-system.md) and [quickmount-system.md](quickmount-system.md) into Measured values, with a tolerance budget that the generator can consume.

## 1. Tool list

| Tool | Use | Qty | Priority |
| --- | --- | --- | --- |
| Digital caliper, 0.01 mm resolution, 150 mm | Slot width, rib width, hole spacing, plate thickness; measure at three points per feature | 1 | Required |
| Feeler gauge set (0.02–1.0 mm) | Slot opening under powder coat, gaps the caliper jaws cannot reach squarely | 1 | Required |
| Digital micrometer, 0–25 mm | Sheet thickness, plate thickness, tab thickness (accurate on accessible edges) | 1 | **Owned** |
| Millimetre tape measure | Overall board and pedal dimensions, model identification | 1 | **Owned** |
| Radius gauge set (1–7 mm) | Slot ends, fillets, keeper radius | 1 | Required |
| Thread pitch gauge + known screws | Pedal and plate screw threads | 1 | Required |
| Digital scale, 0.1 g | Pedal weight, plate mass, load assumptions | 1 | Required |
| Luggage/spring scale, 0–50 kg | Insertion, release, and pull-off force | 1 | Required |
| Macro camera + steel ruler | Contact geometry, keeper cavity; a scale in every photo | 1 | Required |
| Two-part silicone mould putty | Non-destructive impression of the keeper cavity and tab profile; cast in rigid resin to measure | 1 kit | Required |
| Flatbed scanner, 1200 dpi | Silhouettes and printed measurements | 1 | Nice to have |
| Thread checker / tap set (M2.5–M4) | Confirming screw threads by test fit | 1 | Nice to have |
| CT or structured-light scan | Internal geometry without disassembly | — | Optional (outsourced) |
| Digital height gauge | Mounting-plane angle and standoff | 1 | Nice to have |

**Owned already:** digital micrometer (0–25 mm) and a millimetre tape measure.

What the tape can and cannot do: it is accurate enough to identify the board model, measure overall pedal footprints, and locate features to the nearest millimetre. It is **not** accurate enough for slot width, rib width, pitch, or hole centres — those need callipers or feeler gauges. The highest-value additions are therefore a 150 mm digital caliper and a feeler gauge set; silicone putty is the only non-destructive way to capture the keeper cavity.

## 2. Procedure

**No destructive measurement.** Every OEM plate must remain usable. Do not cut, saw, heat, or pry any plate; capture internal geometry with silicone impressions, photography, or an outsourced scan.

### 2.1 Board

1. Photograph the whole top surface with a ruler, plus one close-up of a slot end and one of the sheet edge.
2. Measure the sheet thickness at four corners and the centre (avoid powder coat build-up on edges).
3. Measure slot opening width at three positions along ten different slots, across at least two board families if available.
4. Measure rib width between adjacent slots and the centre-to-centre pitch in both axes from the same reference edge.
5. Measure slot length and end radius.
6. Estimate powder-coat thickness by comparing a coated area with an uncoated reference (for example the sheet's masked underside) using the micrometer; never cut into the board. If no reference exists, record it as Open and treat the slot opening as the governing dimension.
7. Verify the mounting plane: place the board on a flat table, measure the height at the four corners of the slot field, and compute the incline.
8. Measure clearance between the sheet underside and the U-braces at several points.
9. Record MOD slot dimensions separately.

### 2.2 OEM QuickMount plate

1. Weigh and measure the plate: overall length, width, thickness at the pedal face, thickness at the tabs.
2. Photograph both faces on a grid background; trace the outline in CAD at 1:1 scale and compare measured features.
3. Measure the tab: width, thickness, protrusion, lead-in chamfer, and position relative to the screw holes.
4. Press silicone mould putty onto the keeper area to capture the cavity; cast it in rigid resin and measure the cast. Repeat on a second plate of the same type to check repeatability.
5. Measure external wall thicknesses and clearances with the micrometer and callipers. Where an internal dimension cannot be reached, record it as Open rather than estimating.
6. Test the kinematics with the QuickRelease Tool: record the tool's motion and the keeper's resulting displacement.
7. Measure the screws supplied with the plate: thread, length, head type.

If the impressions and external measurements cannot resolve the latch kinematics, options are an outsourced CT/X-ray scan, a request to RockBoard for a drawing, or buying a spare plate later — never modifying the existing set.

### 2.3 Pedal

1. Measure W × D × H with callipers, micrometer, or tape; compare with the manufacturer's published values.
2. Record the screw holes: position relative to a defined datum (use the pedal's bottom centre), thread size, usable depth, and whether the hole is recessed.
3. Photograph the bottom face with a ruler, orthogonally, so the hole coordinates can be digitised.
4. Note rubber feet, battery door, and any overhanging enclosure features.

## 3. Record templates

### 3.1 Board measurement record

| ID | Parameter | Nominal | Measured min | Measured max | Tool | Date | Operator | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B-01 | Slot opening width | | | | Caliper | | | Open |
| B-02 | Slot length | | | | Caliper | | | Open |
| B-03 | Slot end radius | | | | Radius gauge | | | Open |
| B-04 | Rib width | | | | Caliper | | | Open |
| B-05 | Pitch X | | | | Caliper | | | Open |
| B-06 | Pitch Y | | | | Caliper | | | Open |
| B-07 | Sheet thickness | | | | Micrometer | | | Open |
| B-08 | Powder coat thickness | | | | Micrometer | | | Open |
| B-09 | Mounting plane angle | | | | Height gauge | | | Open |
| B-10 | Under-sheet clearance | | | | Depth gauge | | | Open |

### 3.2 OEM plate record

| ID | Parameter | Measured | Tool | Date | Notes |
| --- | --- | --- | --- | --- | --- |
| Q-01 | Mass | | Scale | | |
| Q-02 | Plate thickness at pedal face | | Caliper | | |
| Q-03 | Tab width | | Caliper | | |
| Q-04 | Tab thickness | | Caliper | | |
| Q-05 | Tab protrusion | | Depth gauge | | |
| Q-06 | Keeper travel | | Video + scale | | |
| Q-07 | Insertion force | | Spring scale | | |
| Q-08 | Release force | | Spring scale | | |
| Q-09 | Pull-off force | | Luggage scale | | |
| Q-10 | Cycles to visible wear | | Cycle rig | | |

Keep the filled records in `docs/measurements/` as CSV or Markdown so they can be diffed and reviewed.

## 4. Photographic protocol

Every photograph used for measurement must contain:

1. a rigid scale (steel ruler or calibration card) in the same plane as the feature,
2. the part flat and orthogonal to the camera axis,
3. uniform lighting without specular blow-out on the powder coat,
4. a label with the measurement ID.

Digitise coordinates from a calibrated image only after checking the scale at both ends (lens distortion makes edges unreliable).

## 5. Tolerance budget

The generator will expose a tolerance profile rather than baking in clearances. Starting values for FDM, to be replaced by measured results:

| Contribution | Typical value | How to handle |
| --- | --- | --- |
| Printer XY dimensional error | ±0.10–0.20 mm | Calibrate with a test artefact per vendor profile |
| Elephant-foot flare | 0.10–0.20 mm on first 0.3 mm | Chamfer the bottom edge |
| Material shrinkage | 0.2–0.8 % depending on polymer | Shrinkage coupon per material |
| Slot width variation (powder coat) | Open | Measure; use worst case |
| Micrometer / caliper / tape uncertainty | ±0.005 / ±0.02 / ±1 mm | Use the right tool per feature; record which was used |
| Thermal expansion in service | Small relative to creep | Ignore for fit, include for creep test |

Design clearances:

| Interface | Initial value | Coupon range |
| --- | --- | --- |
| Tab to slot side | 0.30 mm per side | 0.15 / 0.25 / 0.35 / 0.45 |
| Tab to slot end | 0.40 mm | 0.25 / 0.40 / 0.55 |
| Keeper interference | 0.20 mm | 0.10 / 0.20 / 0.30 / 0.40 |
| Screw clearance hole (M3) | 3.4 mm | 3.3 / 3.4 / 3.5 |

These are starting points. Nothing ships until the coupon test confirms the value for the target printer and material.

## 6. Fit coupons

Print a single coupon plate that contains a **clearance ladder**:

- five tab widths: `nominal - 0.30`, `- 0.15`, `nominal`, `+0.15`, `+0.30`
- three keeper interference variants
- labels embossed at 3 mm depth so they survive printing
- one hole per screw size to check clearance

Test each variant by hand-inserting into a real board and recording:

| Variant | Insert | Wobble | Slide along slot | Release | Verdict |
| --- | --- | --- | --- | --- | --- |
| T1 | | | | | |
| T2 | | | | | |
| T3 | | | | | |
| T4 | | | | | |
| T5 | | | | | |

Choose the tightest variant that inserts by hand and does not wobble. Re-run the coupon for every vendor/material combination, and order it through the actual manufacturing route (Kea Modelling) rather than an in-house printer — the vendor's slicer profile is part of the fit.

Order the coupon in two separate orders to measure repeatability, and include the printed calibration features listed in [manufacturing.md §4](manufacturing.md#4-process-calibration-vendor-coupon).

## 7. OEM baseline test protocol

The OEM plate is the reference standard. Measure it before optimising a printed design. All steps are non-destructive; the plate remains serviceable.

1. **Static retention:** mount the plate in a board clamped to a table. Attach a luggage scale and pull vertically, then horizontally, recording peak force before release.
2. **Insertion/release force:** five cycles each with a spring scale; note the direction of the QuickRelease Tool motion.
3. **Cycle life:** 100 insert/release cycles, photographing the keeper every 25 cycles.
4. **Creep:** hang 5 kg from a mounted plate at room temperature for 24 h; repeat at 50 °C and at 70 °C. PETG is the only functional material available from Kea and a closed vehicle can exceed 70 °C, so the 70 °C result is the design-driving case.
5. **Marking:** inspect the powder coat under the tab for scuffs.

Acceptance for a printed plate: at least 80 % of OEM static retention, no permanent set greater than 1 mm, and no board marking.

## 8. Data handling

- Store measurements as CSV with one row per feature and a `status` column (`open`, `measured`, `verified`).
- Record the board model, serial/batch if visible, and purchase date.
- Keep the raw photos in `docs/measurements/<date>/` with the record file alongside.
- Never overwrite a measurement; add a new row with a new date and mark the old one superseded.

## Sources

- RockBoard catalogue: <https://www.rockboard.de/downloads/RockBoard_Catalog.pdf>
- RockBoard QuickMount overview: <https://www.rockboard.de/en/quickmounts/>
- Kea Modelling manufacturing profile: [manufacturing.md](manufacturing.md)
