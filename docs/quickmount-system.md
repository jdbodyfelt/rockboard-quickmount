# QuickMount system

## 1. Official description (Official)

From the RockBoard QuickMount pages and catalogue:

> With a simple click, the QuickMount elements snap securely and firmly into the slot grid of the RockBoard pedalboards and they can be removed just as easily if necessary.

> Simply screw a QuickMount onto each of your pedals using the screws from their back plates (longer screws are also included) and click them into the slot grid on the surface of your RockBoard. Removal is also easy thanks to the QuickRelease Tool.

Key properties for our design:

- The plate attaches to the pedal using the **pedal's own bottom-plate screws**; longer replacement screws are supplied.
- No permanent modification to the pedal is required.
- The plate engages the **same slot grid** as the cable-routing slots.
- Release requires the **QuickRelease Tool**, so retention is not a simple friction fit that can be pulled out by hand.
- The system replaces hook-and-loop tape and avoids adhesive residue.

Sources: <https://www.rockboard.de/en/quickmounts/>, <https://www.rockboard.de/downloads/RockBoard_Catalog.pdf> (pages 19–22).

## 2. Product range (Official)

The catalogue lists roughly 40 QuickMount types. They are best understood as **housing-family plates**, not pedal-specific plates: one type often covers many models from several brands.

Representative types (catalogue pages 20–22):

| Type | Compatibility summary |
| --- | --- |
| A | MXR standard size; Electro-Harmonix nano series |
| B1 | Keeley, EarthQuaker Devices, JHS, Mooer GL 100, Seymour Duncan, Friedman, Wampler EQ/Velvet Fuzz, several Walrus models |
| C | Larger vertical housings: EarthQuaker, EHX, Keeley, MXR, JHS, Darkglass and others |
| D | Larger horizontal housings: EHX, Keeley, MXR; Warwick Gnome amp |
| E | Standard BOSS compact series |
| E200 | BOSS DD-200, EQ-200, IR-200, MD-200, OD-200 |
| F | Standard Ibanez Tube Screamer / Maxon Nine series |
| FT1–FT5 | Specific Fulltone models (OCD, CS-Ranger, Supa-Trem, Deja Vibe, Full-Drive 1/2/3, etc.) |
| G | TC Electronic standard size |
| H | DigiTech compact series |
| I, I1 | Eventide H9; Eventide Blackhole/Knife Drop/MicroPitch/Riptide/Tricera/UltraTap |
| J, J1, J2 | Medium Strymon; BOSS 500-series and Strymon large-format; Strymon Nightsky/Volante |
| K | Mooer micro series; IK Multimedia ToneX One |
| KE | Kemper Profiler Player |
| L | Mini-style housings: MXR, Pigtronix, Xotic, several TC mini pedals |
| L6 | Line 6 HX Stomp |
| LE1–LE4 | Lehle models |
| M | Dunlop Cry Baby standard wah; RockBoard StageTuner ST-02 |
| MR | Meris (Hedra) |
| N | TC-Helicon Harmony Singer 2, Duplicator, Mic Mechanic 2 |
| NRL | Neural DSP Quad Cortex |
| O | Friedman Overdrive Deluxe; Walrus Descent |
| OE | Origin Effects Cali76, Cali76 FET |
| PC1–PC3 | Pro Co Fat Rat, The Rat, Lil Rat |
| SR1, SR2 | Source Audio models |
| TC | TC Electronic compact range |
| UA | Universal Audio compact range |
| UH | Universal horizontal: mounting hole distance 51 × 103 mm and 73–91 mm |
| UV | Universal vertical: 96 × 48 mm |
| WH1–WH3 | Way Huge models |

Accessories in the same family: QuickMount Cable Fix clips, Pick Box, QuickRelease Tool, Second Tier riser, and PedalSafe protection covers (including a PedalSafe variant supplied with a QuickMount plate).

**Plates on hand:** Type E ×2 (BOSS OC-2, OD-3), Type M (wah), Type J1 (Strymon Timeline). See [inventory.md](inventory.md#2-oem-quickmount-plates).

The **UH type publishes a mounting-hole distance**, which is a useful precedent: RockBoard itself treats the screw-hole geometry as the defining dimension of a plate. Our generator should do the same.

## 3. Anatomy we must reverse engineer

The OEM plate is an injection-moulded part (material not published; assume a glass-filled engineering polymer until identified). Its functional zones are:

1. **Pedal interface:** a flat face that sits against the pedal's bottom plate, with clearance holes matching the pedal's screws.
2. **Board interface:** one or more keys/tabs that pass through the slot grid and bear on the sheet.
3. **Retention ("keeper"):** the project brief describes this as a C-shaped pressure lock. Its exact kinematics are not published and are the single most important unknown for a functional clone.
4. **Release feature:** something the QuickRelease Tool pushes, pulls, or rotates to unlock the plate.

What is **not** published and must be captured:

- tab thickness, width, and depth
- keeper travel, preload, and contact area
- whether the lock is positive (interference behind the sheet) or friction-based
- insertion and release directions
- retention force and number of insertion cycles before loosening
- plate thickness at the pedal interface (this is added to the screw stack)
- any ribs or bosses that set the pedal's supported area

> Add dimensioned photographs and a measured drawing to this section once captured. Until then, treat every number as Open.

## 4. Hypotheses to test

These are explicit hypotheses, not facts. Each has a decisive test.

| ID | Hypothesis | Test |
| --- | --- | --- |
| H1 | The tab drops vertically through a slot, then the plate slides along the slot to engage the keeper. | Insert slowly while watching the plate; mark the path with tape; test whether the plate can be removed without sliding. |
| H2 | The keeper is a cam or lever loaded by an integral plastic spring; the QuickRelease Tool rotates or lifts it. | Inspect the tool's tip; probe the keeper with a soft tool; photograph the cavity with a silicone impression. |
| H3 | Retention is primarily interference (the keeper pinches the slot rib) rather than a positive catch behind the sheet. | Pull test with a luggage scale; compare force direction; look for wear marks showing the contact area. |
| H4 | The plate is retained at two slots and cannot rotate. | Try to rotate the mounted plate about one tab; measure angular play. |

Record the outcome in this document and convert the losing hypotheses into "do not design this way" notes.

## 5. Constraints for a printed equivalent

A printed plate cannot assume the OEM's material or process. Constraints:

- **No metal spring by default.** If the design needs spring force, use an integral compliant beam, a captured O-ring, or a screw-actuated clamp. Sourcing a spring is allowed but should be optional.
- **Creep.** A permanently loaded polymer tab will relax, especially at pedalboard-in-a-van temperatures. PLA is unsuitable (and is rejected for functional parts). **PETG is the selected material** because it is the only functional option Kea Modelling offers; ASA and PA-CF are not available from the vendor and exist only as a future in-house fallback. Test at 50 °C and 70 °C, not just room temperature.
- **Layer orientation.** Tabs loaded in bending must not be built from layers that delaminate. Choose print orientation so the load runs along the extrusion direction, and document it in the print profile.
- **Fatigue.** Design for at least the OEM cycle count we measure in Phase 1, with a target of 500 insert/remove cycles for a consumer part.
- **Surface protection.** No sharp edges against the powder coat. Add a lead-in chamfer and radius every contact edge.
- **Serviceability.** A plate that cannot be removed without damaging the board is a failure. Match the OEM's tool-release behaviour unless the user chooses a tool-free variant.
- **Pedal support.** The plate must not become the only thing holding a pedal whose enclosure overhangs. Where needed, add support pads or feet pockets.

## 6. Replacement screws

The plate thickness adds to the screw stack, so original screws often become too short. The OEM solves this by including longer screws. Our generator must:

1. Record the pedal's screw thread and the **usable depth** (not just the hole diameter).
2. Compute the required screw length as `original_length + plate_thickness_at_hole - compressed_rubber_foot` and warn if it exceeds the pedal's safe depth.
3. Offer a bill of materials per design, with standard lengths (e.g. M3 × 8/10/12/16) and a warning against over-driving into a PCB.
4. Never assume a thread. Thread sizes observed on pedals include M2.5, M3, M3.5, M4, and imperial sizes; confirm per pedal.

Open: the exact screw sizes shipped with each OEM type. Measure the included screws from a sample of plates.

## 7. Rubber feet and battery compartments

Many pedals have rubber feet or a battery door on the bottom. Three strategies, in order of preference:

1. **Pockets:** recess the plate so the feet stay on and the pedal sits at its natural height. Adds thickness; may conflict with slot clearance.
2. **Through-holes / reliefs:** let the feet pass through the plate. Simple, but the plate must still support the enclosure around them.
3. **Foot removal:** the OEM approach for some pedals. Document that it may void warranty and reduce grip, and make it an explicit user choice.

Battery doors must remain operable unless the user opts out. If the plate spans a battery door, add a cut-out and a note in the build report.

## 8. Verification protocol per design

A printed plate is only accepted when all of the following pass:

| Check | Criterion |
| --- | --- |
| Screw engagement | Each screw engages at least 4 mm of thread (or the pedal's documented depth) without bottoming out |
| Seating | No visible gap at the pedal interface; no rock when pressed at each corner |
| Insertion | Plate clicks into the slot with hand force; no tools required to install |
| Retention | Pull-off force ≥ 80 % of the measured OEM plate on the same board |
| Release | QuickRelease Tool (or the designed release) unlocks without marking the board |
| Cycles | 100 insert/remove cycles with no visible wear-through of the keeper |
| Creep | 5 kg hanging load for 24 h at 50 °C and at 70 °C with < 1 mm permanent set |
| Board protection | No scratches or powder-coat damage after the cycle test |

## 9. Open questions

1. What material is the OEM plate, and what is its plate thickness?
2. What exactly does the keeper contact, and over what area?
3. Does the keeper need the slot's full length, or does it work anywhere along the slot?
4. Are there variants for board families with different sheet thickness?
5. What retention force does the OEM achieve (our benchmark)?

## Sources

- QuickMount overview: <https://www.rockboard.de/en/quickmounts/>
- QuickMount Finder: <https://www.rockboard.de/en/quickMountFinder/>
- Catalogue, QuickMount section (pages 19–22): <https://www.rockboard.de/downloads/RockBoard_Catalog.pdf>
- Manufacturing constraints: [manufacturing.md](manufacturing.md)
- Project brief: [TODO.md](../.agents/TODO.md)
