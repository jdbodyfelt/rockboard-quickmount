# Equipment inventory

Physical items available for measurement, and how each may be used. Update this file whenever an item is added, borrowed, or destroyed.

Last updated: 2026-10-21.

## 1. Board

| Item | Detail | Status |
| --- | --- | --- |
| RockBoard Quad | Model not yet confirmed (4.1, 4.2, 4.3, or 4.4) | Available |

**Confirm the model** by measuring the overall width and matching it to the catalogue:

| Model | Width | Depth |
| --- | --- | --- |
| Quad 4.1 | 470 mm | 330 mm |
| Quad 4.2 | 622 mm | 330 mm |
| Quad 4.3 | 828 mm | 330 mm |
| Quad 4.4 | 722 mm | 330 mm |

A 622 mm width identifies 4.2; 722 mm identifies 4.4. Record the confirmed model in the board profile and in [rockboard-system.md](rockboard-system.md).

## 2. OEM QuickMount plates

Plate types are inferred from RockBoard's compatibility lists and must be confirmed from the part number moulded on the underside.

| Plate for | Expected type | Product no. | Qty | Destructive test? |
| --- | --- | --- | --- | --- |
| BOSS OC-2 | Type E (BOSS compact) | RBO B QM T E | 2 (with OD-3) | **Yes — one may be sectioned** |
| BOSS OD-3 | Type E (BOSS compact) | RBO B QM T E | (second unit) | Keep intact as the fit reference |
| Wah pedal | Type M (Dunlop Cry Baby standard) | RBO B QM T M | 1 | No — non-destructive only |
| Strymon Timeline | Type J1 (BOSS 500-series / Strymon large-format) | RBO B QM T J1 | 1 | No — non-destructive only |

Why this matters: Type E is the only type with a **spare**, so it is the only plate we may cut for a cross-section. Type M and J1 are singletons and must be measured with callipers, photography, and silicone impressions only.

Confirm each type by looking for the moulded product number (format `RBO B QM T <type>`) on the plate's underside.

## 3. Pedals

| Pedal | Housing | Use in the project |
| --- | --- | --- |
| BOSS OC-2 | BOSS compact | Screw-pattern measurement; compares directly with the Type E plate |
| BOSS OD-3 | BOSS compact | Second Type E sample; confirms batch consistency |
| Dunlop wah (model TBC) | Wah housing | Screw pattern for the Type M plate |
| Strymon Timeline | Large-format Strymon | Screw pattern for the Type J1 plate |

The two BOSS compact pedals give a useful repeatability check: if the same plate fits both, the Type E hole pattern covers the family's variation.

## 4. Gaps

| Missing item | Impact | When needed |
| --- | --- | --- |
| Duo, Tres, or Cinque board | Cannot confirm the slot grid is common across families | Phase 3 (or earlier if borrowed) |
| Spare Type M and J1 plates | No destructive cross-section for those keeper designs | Only if non-destructive measurement is insufficient |
| Duplicate OEM plate for cycle testing | The retention baseline uses the user's only copy of M/J1 | Phase 1 (Type E duplicate covers the baseline test) |

## 5. First measurement session

Order of work, using only what is on hand. Budget roughly half a day.

1. **Identify the board model** by width; photograph the label and a slot close-up.
2. **Measure the board** with the `B-01` to `B-10` record in [geometry-capture.md](geometry-capture.md#31-board-measurement-record): slot width, length, end radius, rib width, pitch, sheet thickness, powder coat, plane angle, under-sheet clearance.
3. **Measure both Type E plates** non-destructively (`Q-01` to `Q-10`), then **section one** along the keeper axis and scan the cross-section.
4. **Photograph and measure the BOSS compact pedals** (OC-2, OD-3): footprint, height, weight, screw positions, thread, depth.
5. **Measure Type M and J1** with callipers and silicone impressions. Do not cut.
6. **Record the OEM baseline** (insertion, release, pull-off, 100 cycles, creep at 50 °C and 70 °C) using one Type E plate on the Quad.
7. File the records and photos under `docs/measurements/<date>/`.

## 6. Handling notes

- Keep one Type E plate untouched until the baseline tests are complete; section the other only after the non-destructive record is filed.
- The QuickRelease Tool is required to remove plates safely; do not lever them out with a screwdriver.
- Photograph every part before disassembly so hole positions and orientation are recoverable.
- Store the sectioned plate in a labelled bag with the measurement ID; it is a reference artefact.

## 7. Related documents

- Measurement procedure: [geometry-capture.md](geometry-capture.md)
- Board parameters: [rockboard-system.md](rockboard-system.md#5-parameters-we-must-measure)
- OEM plate types: [quickmount-system.md](quickmount-system.md#2-product-range-official)
