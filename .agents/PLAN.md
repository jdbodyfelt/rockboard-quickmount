# PLAN — Custom RockBoard QuickMount-compatible pedal mounts

From a pedal name (or a YAML/photo input) to a printable STL that clicks into a RockBoard slot grid and holds a pedal securely.

Preparation evidence lives in [docs/](../docs/README.md). Open dimensions are tracked there and are not repeated here except where they gate a phase.

---

## 1. Objective and definition of done

**Objective:** generate, validate, and batch-produce custom pedal mounting plates that are mechanically compatible with Warwick RockBoard's slot grid and QuickMount retention scheme, for pedals the OEM does not cover.

**Definition of done for v0.1 (MVP):**

1. `qm generate --pedal <id>` produces a watertight STL, a STEP for review, and a manifest with full provenance.
2. The part installs by hand into a real board, locks, and releases with the intended mechanism.
3. It passes every check in [quickmount-system.md §8](../docs/quickmount-system.md#8-verification-protocol-per-design) when printed by Kea Modelling in PETG, including ≥ 80 % of the measured OEM pull-off force and 100 insert/remove cycles.
4. `qm batch` processes at least ten pedals in one command with a per-item report and no manual edits.
5. For a pedal with an official QuickMount type, no per-pedal screw measurement is needed.
6. Every number used in a generated design is traceable to a source at the required confidence level.
7. Documentation covers the board, the OEM system, the measurement method, the data model, and the pipeline.

**Non-goal for v0.1:** a polished GUI. The CLI and the data files are the product.

---

## 2. Design principles

1. **Measure before modelling.** An Open dimension is a blocker, not a default. Test coupons decide clearances, not intuition.
2. **One interface, one module.** The slot/keeper profile is a single parametrised module shared by coupons and production parts.
3. **Data has provenance.** Every dimension carries a confidence level and a source; generation refuses to run below the gate.
4. **OEM plates are the reference standard.** Retention, thickness, and cycle life are benchmarked against a real QuickMount.
5. **Deterministic output.** Same inputs, pinned tools, same result; manifests make a print reproducible.
6. **Fail loudly.** A missing measurement, an unprintable wall, or a questionable record aborts the build with a clear message.
7. **Printable by the chosen vendor.** Design for Kea Modelling's FDM process in PETG, with no supports on mating faces.

---

## 3. Architecture

```
┌────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│ Input          │     │ Resolver         │     │ Catalog            │
│ - pedal name   │────►│ - identity       │────►│ - pedals (YAML)    │
│ - YAML         │     │ - OEM type map   │     │ - board profiles   │
│ - photo card   │     │ - confidence gate│     │ - QuickMount types │
└────────────────┘     └────────┬─────────┘     └────────────────────┘
                                │ complete record
                                ▼
                       ┌──────────────────┐
                       │ Parameter        │
                       │ resolver + schema│
                       └────────┬─────────┘
                                ▼
                       ┌──────────────────┐     ┌──────────────────┐
                       │ CAD kernel       │────►│ Validator        │
                       │ build123d        │     │ gates + checks   │
                       └────────┬─────────┘     └────────┬─────────┘
                                ▼                        ▼
                       ┌──────────────────┐     ┌──────────────────┐
                       │ STL / STEP       │     │ Manifest + report│
                       └──────────────────┘     └──────────────────┘
```

Two closed loops sit outside this diagram and are part of the plan:

- **Metrology loop:** board/OEM measurements → board profile + type library → coupons → validated printer profile.
- **Physical validation loop:** printed part → retention, creep, cycle tests → design or parameter revision.

---

## 4. Workstreams

| Workstream | Scope | Primary phases |
| --- | --- | --- |
| **A. Metrology & interface** | Board and OEM plate measurement, slot/keeper model, coupons, print orientation | 0, 1, 3 |
| **B. Generator** | Schema, parameter resolution, CAD features, validation, export | 2, 4, 6 |
| **C. Pedal data** | Type library, pedal catalogue, lookup automation, photo measurement | 3, 5 |
| **D. Validation** | OEM baseline, physical tests, CI regressions, field feedback | 1, 2, 4, 6 |
| **E. Documentation** | `/docs`, examples, release notes | 0, 6 |

Workstream A gates B and C. B and C can then run in parallel. D runs continuously. E closes each phase.

---

## 5. Phased plan

Summary:

| Phase | Name | Effort (person-days) | Depends on | Gate |
| --- | --- | --- | --- | --- |
| 0 | Foundations and documentation | 1–2 | — | Docs reviewed; measurement kit specified |
| 1 | Reference characterisation and slot interface | 4–6 | 0 | Printed coupon locks into a real board and meets retention target |
| 2 | Plate generator MVP | 5–7 | 1 | Three real pedals designed, printed, and accepted |
| 3 | OEM type library and pedal mapping | 4–6 | 1 | ≥ 10 types measured; ≥ 50 pedals catalogued |
| 4 | Batch and QA | 3–4 | 2, 3 | Ten-pedal batch in one command; CI green |
| 5 | Automated lookup and photo measurement | 6–9 | 3 | Name → gated record for ≥ 20 pedals |
| 6 | Hardening and v0.1 release | 3–4 | 2–5 | Tagged release with examples and profiles |

Total: roughly 26–38 person-days, excluding printing time and hardware purchases.

### Phase 0 — Foundations and documentation

**Deliverables**

- [x] `docs/` set: board, QuickMount, metrology, pedal data, manufacturing, pipeline, schema, sources.
- [x] This plan.
- [x] Manufacturer confirmed: Kea Modelling (FDM, PETG and PLA).
- [x] Equipment inventory recorded: Quad board, Type E plates ×2, Type M plate, Type J1 plate ([inventory.md](../docs/inventory.md)).
- [ ] Confirm the Quad model by width and each plate's moulded product number.
- [x] Metrology kit on hand: caliper (inside/outside jaws), micrometer, tape, feeler gauges, silicone putty, spring/luggage scale, 0.1 g scale. No purchases required.
- [ ] Vendor questions sent; answers logged in [manufacturing.md §7.1](../docs/manufacturing.md#71-response-log).
- [ ] Calibration coupon specification ready; ordering deferred until the vendor answers.
- [ ] Decide whether an in-house printer is available for fast iteration (Kea dispatch is 3–4 days).

**Exit criteria:** documents reviewed; every Open parameter has an owner and a method; vendor capability questions answered or scheduled; budget for OEM plates and vendor coupons approved.

**Immediate risks:** the keeper geometry may not be printable at all with commodity filament. Phase 1 exists to find out early and cheaply.

### Phase 1 — Reference characterisation and slot interface

**Goal:** prove the interface before building the product around it.

**Work**

1. Measure the Quad board (confirm 4.x) using [geometry-capture.md](../docs/geometry-capture.md); add a second board family in Phase 3 or earlier if one can be borrowed.
2. Use the Type E pair on hand: characterise both externally and compare them for repeatability; capture the keeper cavity with silicone impressions. Measure the Type M and Type J1 plates the same way. **No plate may be sectioned** — see [inventory.md](../docs/inventory.md).
3. Measure OEM baseline: insertion, release, pull-off, 100 cycles, creep at 50 °C and 70 °C.
4. Build the parametric slot profile with three load-bearing features: tab, keeper, release.
5. Build the coupon generator (clearance ladder + interference variants).
6. Once the vendor has answered, order the vendor calibration coupon from Kea in two separate orders; measure shrink, holes, walls, and snap beams ([manufacturing.md §4](../docs/manufacturing.md#4-process-calibration-vendor-coupon)).
7. A/B test print orientations for retention, submitting both orientations to Kea.
8. Decide the retention mechanism: integral compliant keeper vs screw clamp vs captured spring.

**Deliverables:** completed measurement records; a completed Quad board profile; `cad/slot_profile.py`; coupon sets; a validated `kea_petg` printer profile; a written decision record for the keeper mechanism and print orientation.

**Exit criteria:** a Kea-printed PETG coupon inserts by hand, locks, resists at least 80 % of the OEM pull-off force, releases cleanly, and survives 100 cycles without visible wear-through.

**Kill/pivot criteria:** if no printed keeper variant reaches 50 % of OEM retention after two design iterations, pivot to a hybrid design (printed plate + purchased spring or a screw-actuated clamp) and re-baseline the plan.

### Phase 2 — Plate generator MVP

**Goal:** one pedal in, one accepted part out.

**Work**

1. Implement schemas and the parameter resolver ([input-schema.md](../docs/input-schema.md)).
2. Implement plate outline, screw bosses, foot pockets, and battery cut-outs on top of the slot profile.
3. Implement the validation gates from [rendering-pipeline.md §4](../docs/rendering-pipeline.md#4-validation-gates).
4. Export STL + STEP + manifest; deterministic naming.
5. Build a small example set with three pedals of different sizes and mounting styles.
6. Print via Kea in PETG, test, and record results; feed findings back into the `kea_petg` vendor profile and log the quote and lead time.

**Exit criteria:** three pedals pass the physical acceptance checks; `qm validate` catches intentionally broken inputs; manifests reproduce the same geometry.

### Phase 3 — OEM type library and pedal mapping

**Goal:** remove per-pedal screw measurement wherever the OEM already solved it.

**Work**

1. Measure the hole patterns and plate thickness of the highest-value types. Suggested start: A, E, L, M, F, J1, and the universal UH/UV.
2. Encode the manufacturer's compatibility lists as a type → pedal mapping (Official source).
3. Add housing-family fallbacks for pedals without an official type.
4. Extend board profiles to at least one complete family per series.
5. Build the pedal catalogue to at least 50 pedals with per-field provenance.

**Exit criteria:** for any pedal on RockBoard's compatibility lists, the generator can build a plate without pedal measurement; catalogue entries validate; the type library is reviewed by a second person.

### Phase 4 — Batch and QA

**Goal:** produce a rig's worth of plates in one run.

**Work**

1. Batch manifest, process pool, per-item error isolation.
2. `report.json` and `report.md`; confidence summary per item.
3. CI: schema tests, geometry regression by volume/bbox/hole coordinates, manifold checks, lint, types.
4. Golden example corpus regenerated nightly.
5. Performance: generation under 10 s per plate; batch of ten under two minutes on a laptop.

**Exit criteria:** ten-pedal batch completes unattended; one deliberately broken pedal does not abort the others; CI is green on Windows and Linux.

### Phase 5 — Automated lookup and photo measurement

**Goal:** make the ideal use case real: type a pedal name, get a gated record, then an STL.

**Work**

1. Identity resolution with aliases and ambiguity prompts.
2. Local-first resolver, then OEM compatibility map, manufacturer pages, retailer specs, and general search — all with caching, rate limits, and terms compliance.
3. Schema-constrained extraction with mandatory quotes and URLs; no value without evidence.
4. Confidence scoring and the generation gate.
5. Printable calibration card and photo rectification; user confirmation UI in the terminal or a simple local page.
6. Accuracy evaluation: compare automated records against manual measurements for at least 20 pedals.

**Exit criteria:** ≥ 80 % of required fields correct against manual ground truth for the evaluation set; zero unverified numbers reach a generated design; every miss degrades to a clear prompt.

### Phase 6 — Hardening and v0.1 release

**Work**

1. Packaging, install instructions, pinned dependencies, CI release artefacts.
2. Complete example set and a "first print" walkthrough.
3. Safety and warranty notes: load limits, material choice, screw replacement, no permanent pedal modification.
4. Licence review and third-party notices.
5. Tag `v0.1.0`; publish release notes with known limitations.

**Exit criteria:** a new user can install, generate, print, and mount one pedal by following the documentation without asking questions.

---

## 6. Milestones

| Milestone | Evidence | Phase |
| --- | --- | --- |
| **M0 — Documented** | `docs/` and `.agents/PLAN.md` merged | 0 |
| **M1 — Interface proven** | Printed coupon locks into a real board and passes retention | 1 |
| **M2 — Pedal to STL** | Three accepted printed plates | 2 |
| **M3 — Type coverage** | Ten types measured; 50 pedals catalogued | 3 |
| **M4 — Batch production** | Ten-pedal batch report | 4 |
| **M5 — Name to STL** | Gated lookup evaluation | 5 |
| **M6 — v0.1.0** | Tagged release and walkthrough | 6 |

---

## 7. Validation strategy

**Layers, cheapest first:**

1. **Unit tests** for parameter resolution, schema rules, and geometry helpers.
2. **Geometric gates** in the generator (manifold, wall thickness, hole positions, slot interference).
3. **Coupon tests** per vendor/material, including a Kea-printed calibration coupon, before any production part.
4. **Physical acceptance** per design: screws, seating, insertion, retention, release, cycles, creep, marking.
5. **Field feedback** from real users after release, feeding the printer profiles and the catalog.

**Test artefacts to keep in the repository:**

- `tests/golden/` — parameter sets with expected volume, bounding box, and hole coordinates.
- `examples/` — three to five pedals covering different mounting styles.
- `docs/measurements/` — dated measurement records and photos.

**Definition of a regression:** any change that moves a golden volume by more than 1 % or a hole centre by more than 0.05 mm must be explained in the commit.

---

## 8. Risks and mitigations

| # | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | Printed keeper cannot match OEM retention or cycle life | Medium | High | Phase 1 gate; hybrid fallback (purchased spring or screw clamp) |
| R2 | Slot dimensions vary between production batches or models | Medium | High | Phase 1 measures the Quad; confirm cross-family consistency in Phase 3 with borrowed or purchased boards; publish the measured range |
| R3 | Pedal screw data is unavailable at scale | High | Medium | OEM type library plus housing families; photo measurement; explicit prompts |
| R4 | Original screws are too short after adding plate thickness | High | Medium | Screw BOM per design; replacement lengths; depth checks |
| R5 | PETG creep at vehicle temperatures causes the pedal to loosen | Medium | High | PETG is the only functional material at Kea; creep tests at 50 °C and 70 °C; keeper preload margin; in-house ASA/PA-CF fallback |
| R6 | Layer orientation makes tabs brittle | Medium | High | Orientation A/B test; request orientation in the order note; documented default |
| R7 | Plate damages the powder coat | Medium | Medium | Radii and lead-ins; marking check in acceptance |
| R8 | Board families have incompatible slot geometry | Low | High | Board profiles are per family; test matrix covers each family |
| R9 | Lookup invents or misattributes data | Medium | High | Evidence-required extraction; confidence gate; human confirmation |
| R10 | Terms-of-service or licence violation when sourcing data | Low | High | Respect robots/terms; no unlicensed datasets; cite and cache only |
| R11 | Vendor-to-vendor or batch-to-batch variation breaks fits | High | Medium | Coupon per vendor profile; clearance profile per vendor; two calibration orders |
| R12 | Licensing/patent concerns for a commercial clone | Low | High | Non-commercial intent; interoperability framing; legal review before selling |
| R13 | Kea's DFM and tolerance are unpublished | High | High | Vendor coupon before production; conservative clearances; validation gates; ask the consultation questions |
| R14 | Single vendor with 3–4 day dispatch slows iteration | Medium | Medium | Batch experiments per order; optional in-house printer; standard STL output keeps vendors interchangeable |
| R15 | Instant-order limits (500 g per part, 10 files per order) | Low | Low | Batch splitter; expected plates are tens of grams |
| R16 | Vendor terms grant an image-marketing licence by default | Low | Low | Request an opt-out before sharing confidential designs |
| R17 | Internal keeper geometry cannot be resolved without cutting a plate | Medium | High | Silicone impressions, macro photography, outsourced CT/X-ray, OEM drawing request; buy a spare later only if needed |

---

## 9. Decisions required

| Decision | Options | Recommendation | Needed by |
| --- | --- | --- | --- |
| Manufacturer | Kea Modelling / in-house / other | **Kea Modelling** (FDM, Mt Eden, Auckland; 330 × 320 × 325 mm) | Decided |
| CAD kernel | build123d / CadQuery / OpenSCAD | **build123d** (Apache-2.0, Python-native, STEP export) | Phase 2 |
| Retention mechanism | Compliant printed keeper / screw clamp / captured spring | Decide from Phase 1 A/B results; start with compliant keeper | Phase 1 |
| Default material | PETG / PLA / other | **PETG** — PLA rejected for heat and creep; ASA/PA-CF are not offered by Kea | Decided |
| Screw strategy | Reuse original / supply replacements / user choice | Supply a BOM and let the user choose; validate depth | Phase 2 |
| Rubber feet | Pocket / through-hole / remove | **Pocket when possible**, user choice otherwise | Phase 2 |
| Release mechanism | Tool-operated (OEM parity) / tool-free | OEM parity first; tool-free as an option | Phase 1 |
| Minimum board coverage | One family / one per series / all | **One per series** (Duo, Tres, Quad, Cinque) | Phase 3 |
| Distribution | Personal / open-source / commercial | Open-source under the existing GPL-3.0; legal review before any sale | Phase 6 |
| Lookup automation scope | Local only / vendor sites / general web | Local + vendor site; general web last, evidence-only | Phase 5 |

---

## 10. Out of scope

- Printing a full pedalboard. We model only the top surface with its slot grid, and only as a reference/validation object.
- Copying OEM plates dimension-for-dimension for resale.
- Supporting non-RockBoard boards in v0.1 (the architecture allows it later).
- Motorised or robotic assembly.
- Pedal electronics, audio, or power design.
- A hosted web service or user accounts.

---

## 11. Repository layout

```
.agents/                  planning and backlog
  PLAN.md                 this document
  TODO.md                 project brief and backlog
docs/                     preparation documentation and measurements
  measurements/           dated CSV records and photos (created when measuring)
quickmount/               Python package (Phase 2)
  cad/
  catalog/
  lookup/
  params/
  validate/
tests/                    unit tests and golden geometry
examples/                 example pedals and manifests
```

---

## 12. Immediate next actions

1. Buy the metrology additions (digital calipers, feeler gauges, silicone mould putty); no plates needed — the owned set covers Types E, M, and J1.
2. Confirm the Quad model by width, measure the board, and fill the board record tables.
3. Capture all four OEM plates non-destructively (callipers, photography, silicone impressions); complete the plate records. Do not section any plate.
4. Run the OEM baseline protocol and write the numbers into [docs/quickmount-system.md](../docs/quickmount-system.md).
5. Implement the slot profile and the coupon generator; print the clearance ladder.
6. Review the Phase 1 gate before writing any product code.

---

## 13. Related documents

- [docs/README.md](../docs/README.md) — index and open questions
- [docs/rockboard-system.md](../docs/rockboard-system.md) — board geometry and parameters
- [docs/quickmount-system.md](../docs/quickmount-system.md) — OEM system and design constraints
- [docs/geometry-capture.md](../docs/geometry-capture.md) — measurement procedure and tests
- [docs/manufacturing.md](../docs/manufacturing.md) — Kea Modelling profile, PETG decision, design rules and vendor calibration
- [docs/pedal-data.md](../docs/pedal-data.md) — data sources and lookup
- [docs/rendering-pipeline.md](../docs/rendering-pipeline.md) — CAD/STL pipeline
- [docs/input-schema.md](../docs/input-schema.md) — YAML formats
- [docs/sources.md](../docs/sources.md) — citations
- [TODO.md](TODO.md) — original project brief
