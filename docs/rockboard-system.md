# RockBoard pedalboards

## 1. Construction (Official)

RockBoard boards are built from a **single sheet of cold-rolled aluminium** supported by U-shaped vertical braces. The top sheet is powder-coated and perforated with a slot grid. The catalogue advertises:

- sturdy, lightweight cold-rolled aluminium construction
- slotted design for easy pedal mounting
- mounting holes for the RockBoard LED light (sold separately)
- U-shaped support braces
- **10° angled surface**
- seamless, black powder-coated surface

Source: RockBoard catalogue, <https://www.rockboard.de/downloads/RockBoard_Catalog.pdf> (retrieved 2026-10-21), and <https://www.rockboard.de/en/>.

The exact meaning of "10° angled surface" still needs confirmation: it may describe a top surface inclined relative to the floor, or a front/rear lip. This matters for the plate's underside and for the pedal's resulting stance; see [§4](#4-mounting-plane-and-coordinate-system).

## 2. Model matrix (Official)

Overall board dimensions (W × D) and weight, from the catalogue size-comparison page. These are board envelopes, **not** the usable slot field.

| Family | Model | Width × Depth | Weight |
| --- | --- | --- | --- |
| Duo | 2.0 | 31.8 × 14.2 cm | 0.5 kg |
| Duo | 2.1 | 47.0 × 14.2 cm | 0.7 kg |
| Duo | 2.2 | 62.2 × 14.2 cm | 0.9 kg |
| Duo | 2.3 | 72.2 × 14.2 cm | 1.0 kg |
| Tres | 3.0 | 44.2 × 23.6 cm | 0.95 kg |
| Tres | 3.1 | 52.2 × 23.6 cm | 1.2 kg |
| Tres | 3.2 | 59.8 × 23.6 cm | 1.3 kg |
| Tres | 3.3 | 72.2 × 23.6 cm | 1.5 kg |
| Quad | 4.1 | 47.0 × 33.0 cm | 1.5 kg |
| Quad | 4.2 | 62.2 × 33.0 cm | 2.05 kg |
| Quad | 4.3 | 82.8 × 33.0 cm | 2.4 kg |
| Quad | 4.4 | 72.2 × 33.0 cm | 3.0 kg |
| Cinque | 5.2 | 62.2 × 42.4 cm | 3.95 kg |
| Cinque | 5.3 | 82.0 × 42.4 cm | 4.5 kg |
| Cinque | 5.3 MAX | 82.6 × 49.8 cm | not captured |
| Cinque | 5.4 | 100.2 × 42.4 cm | 5.1 kg |

Height including rubber feet for Duo 2.0: **35–58 mm** (Official, <https://www.rockboard.de/en/pedalboards/duo-20/>). Confirm per model before relying on under-board clearance.

## 3. Slot grid

The top sheet is a **slot-based grid**: long slots that serve both cable routing and pedal mounting. QuickMount plates engage the same grid, which is why the system is board-model independent in principle.

Two slot families must be distinguished:

| Family | Purpose | Availability |
| --- | --- | --- |
| **Mounting/cable slots** | Accept QuickMount tabs; route cables; general accessory mounting | All models |
| **MOD slots** | Wider slots for MOD patchbays, drawers, and other MOD accessories | Tres, Quad, Cinque (Open: confirm exact models) |

Evidence that MOD slots are not universal: the catalogue's rotating drawer "fits MOD slots in RockBoard pedalboards (except RockBoard DUO 2.0, 2.1, 2.2, and 2.3)". Treat the Duo family as having no usable MOD slots until measured.

Also Open:

- slot orientation (longitudinal vs transverse)
- number of slot columns/rows per model
- slot pitch (centre-to-centre) in both axes
- whether the grid and pitch are identical across Duo/Tres/Quad/Cinque
- whether the slot field is inset from the board edges and by how much

## 4. Mounting plane and coordinate system

Define the design frame now so every measurement and every CAD feature uses the same datum:

- **Origin:** centre of the plate footprint, on the plate's underside (the face that contacts the board).
- **+X:** along the board's long axis.
- **+Y:** across the board's depth.
- **+Z:** away from the board surface (toward the pedal).
- **Units:** millimetres everywhere in code, data, and filenames.

The plate's underside must be planar and sit flat on the powder-coated sheet. If the top sheet is actually inclined by 10°, the plate still needs only a planar underside; the pedal simply stands at that angle. The angle becomes a design input only if we add risers or second-tier adapters.

Things that affect the mounting plane:

1. **Powder coat thickness.** It narrows the slot opening and adds a small standoff. Measure at several points; it is a real part of the fit.
2. **Sheet thickness.** Governs how much tab length can engage and how much load the slot edge tolerates.
3. **Brace positions.** U-shaped braces under the sheet may limit where a tab can protrude below the surface.
4. **Rubber feet.** They set the board's ground clearance and can interfere with long tabs.

## 5. Parameters we must measure

| Parameter | Symbol | Why it matters | Status |
| --- | --- | --- | --- |
| Slot opening width | `slot_w` | Primary sliding/insertion fit | Open |
| Slot length | `slot_l` | Tab length and keeper travel | Open |
| Slot end radius | `slot_r` | Corner clearance on tabs | Open |
| Rib width between slots | `rib_w` | Maximum keeper footprint without bridging | Open |
| Slot pitch (X, Y) | `pitch_x`, `pitch_y` | Multi-tab plates align with two or more slots | Open |
| Sheet thickness | `t_sheet` | Tab engagement depth, stiffness | Open |
| Mounting plane angle | `angle_board` | Pedal stance, riser design | Open |
| Powder coat thickness | `t_pc` | Effective slot width reduction | Open |
| Slot edge chamfer/radius | `chamfer` | Insertion lead-in, wear | Open |
| MOD slot width/length/pitch | `mod_*` | Accessory compatibility, avoid overlap | Open |
| Usable slot field margins | `margin_x`, `margin_y` | Plate placement limits | Open |
| Under-board clearance to braces | `clr_brace` | Maximum tab protrusion | Open |

Measurement procedure and record template: [geometry-capture.md](geometry-capture.md).

## 6. Design implications

- **Two-slot engagement.** A plate held by a single tab can rotate. Prefer tabs in two slots spaced as far apart as the pedal allows; fall back to one tab plus a bearing pad if the pedal is too small.
- **Avoid point loads.** Load should be spread along the slot edge, not concentrated at a corner. Prefer a keeper that clamps over a length of rib rather than a single pin.
- **Never rely on the powder coat for retention.** It is a thin, brittle layer; design metal-to-metal contact through the slot, with clearance that does not scrape.
- **Respect the cable function.** Slots under a plate stop being usable for cables. Keep at least one adjacent slot free where possible.
- **Do not cover LED mounting holes or MOD slots** unless the user explicitly wants that.
- **Plan for multiple board families.** If the pitch differs between families, the board profile is a generator parameter and the test matrix must cover one board from each family.

## 7. Open questions

1. Is the slot grid identical across all current families and across production years?
2. Does the Duo family really have no MOD slots, and does that change the usable mounting area?
3. Is the "10° angled surface" an incline of the whole top sheet?
4. What is the maximum pedal weight the OEM plates are rated for? (Not published; derive by test.)
5. Are there left/right-handed variants of the slot pattern near board edges?

## Sources

- RockBoard catalogue (PDF): <https://www.rockboard.de/downloads/RockBoard_Catalog.pdf>
- RockBoard pedalboards overview: <https://www.rockboard.de/en/pedalboards/>
- Duo 2.0 product page: <https://www.rockboard.de/en/pedalboards/duo-20/>
- RockBoard home: <https://www.rockboard.de/en/>
