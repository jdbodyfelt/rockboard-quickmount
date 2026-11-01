# QuickMount mechanism — mechanical analysis

How the RockBoard slot grid and the various QuickMount-compatible clips actually
work, derived from mesh analysis of published clip models and from RockBoard's
own documentation. This document drives the design of the generator.

## 1. Licence note on the analysed models

The analysis in §3 uses the Thingiverse part set *"Rockboard: Base Plate Clips for
Boss, MXR, EHX & Gamechanger Plasma, Morningstar MC6"* by **TAPOR**
(<https://www.thingiverse.com/thing:6894147>), licensed
**CC BY-NC-SA** (attribution, non-commercial, share-alike).

That licence is **incompatible** with redistributing derived CAD in this
GPL-3.0 repository for commercial use. Therefore:

- the reference files are **not committed** (`reference/` is git-ignored);
- only *measurements and mechanism understanding* are carried forward, which are
  facts, not protected expression;
- no geometry from those files is copied into the generator.

The generator's design in §5 is an independent mechanism choice.

## 2. Method

The STLs were measured numerically with the tools in `tools/`:

- `stl_section.py` — ASCII occupancy map of a planar section in **world**
  coordinates (axis-labelled, so orientation is unambiguous);
- `stl_profile.py` — exact section polygon vertices in world coordinates;
- `stl_render.py` — shaded multi-view renders.

Plan-view (constant-Z) area-and-extent sweeps located the plate plane and the
hook features; cross-sections normal to X and Y gave the hook profile.

## 3. What the reference parts actually are

Six STLs were analysed. Three are complete pedal interface plates (Boss, MXR/EHX,
Gamechanger Plasma); three are bare clips (a 2-slot, a 3-slot, and a Morningstar
plate). Measured extents:

| Part | X | Y | Z | Volume | Notes |
| --- | --- | --- | --- | --- | --- |
| `Rockboard_Boss_Base_+_Clip` | 61.0 | 116.5 | 20.89 | 35 640 mm³ | plate 61 × 116.5 × 4.2 + two hook housings |
| `Rockboard_Mxr_-_EHX_Clip` | 60.5 | 114.8 | 18.0 | 16 464 mm³ | plate 60 × 112 × 2 at the top of Z |
| `Rockboard_Gamechanger_Plasma_Pedal` | 96.5 | 138.0 | 17.9 | 27 862 mm³ | no-hole variant, taped to the pedal |
| `Morningstar_MC_6_Rockboard_Clip_no_holes` | 145.0 | 91.0 | 18.6 | 30 390 mm³ | no-hole variant, taped to the pedal |
| `Rockboard_3_Slot_Clip` | 22.09 | 114.8 | 17.88 | 7 500 mm³ | bridge with a hook at each end |
| `Rockboard_2_space_Clip` | 69.0 | 16.0 | 19.64 | 4 595 mm³ | bridge with a hook at each end, 16 mm wide |

### 3.1 The engagement feature is a *pair of walls straddling a rib*

Taking the Boss plate as the clearest example, a constant-Z sweep shows:

| z (mm) | Cross-section |
| --- | --- |
| 0.2 – 2.2 | full plate 61 × 116.5 (area 7099 mm²) |
| 3.2 – 4.2 | reduced plate 53 × 108.5 (area 5714 mm²) — a 4 mm rim, 2 mm step |
| 5.2 | two bars only, X −29.5…−7.5, Y −35.3…−32.8 and 43.3…45.8 |
| 6.2 – 18.2 | **four** bars, each 2.5–3 mm thick, 22.2 mm long in X |
| 19.2 – 20.9 | the bars of each pair merge into a dome |

So each hook is a **hollow arch**: two walls 12.5 mm apart (inner faces
−35.3 and −47.8), each ~3 mm thick, 22.2 mm long, about 13 mm tall, closed at the
top. One wall of each arch carries an outward **barb** that appears between
z = 6.0 and 11.25 (outer face steps from −47.8 → −50.85 → −52.15, i.e. 1.4 and then
2.9 mm proud).

Reading that in assembly terms: the arch **drops over a slot rib**; its two walls
sit down inside the two slots either side of that rib; the barbs project into
those slots and catch the **underside of the sheet**. Lift the pedal and the
barbs press on the sheet underside — a positive, non-friction lock.

The 2-slot clip is the same idea reduced to a bare spring: a 35.5 × 16 strip whose
ends curl up and back over, the arms 2.5 mm thick with a 14.3 mm gap between them,
tips pointing inward. The author's own render describes it as a strip that "curls
into a half-cylinder shape at both ends".

### 3.2 Consistent dimensions across independent designs

| Feature | Boss plate | 2-slot clip | MXR/EHX plate | Derivation |
| --- | --- | --- | --- | --- |
| Gap between hook walls | 12.5 mm | 14.3 mm | ~13 mm | ≈ **rib width** |
| Wall thickness | 2.5–3.0 mm | 2.5 mm | ~3 mm | must fit inside the slot |
| Barbs proud of wall | 2.9 mm | inward hooks | 1–3 mm | under-sheet engagement |
| Plate thickness | 4.2 mm (2 + 2 stepped) | 2.0 mm | 2.0 mm | screw stack added |
| Hook depth (plate face to sheet bite) | ~6–11 mm | ~7 mm | ~5–7 mm | standoff |

Three independently modelled parts agreeing on a **rib of ~12.5–14.3 mm** is the
strongest evidence available without callipers on the board. The **sheet
thickness** shows up as a 2.25 mm step in the 3-slot clip and 2.0 mm plate
thicknesses, consistent with 2.0 mm cold-rolled aluminium plus powder coat.

### 3.3 Kinematics and failure modes

| Behaviour | Finding |
| --- | --- |
| Insertion | The hook cannot be pushed straight in: the barb is wider than the throat. Every reference part relies on either a long lead-in ramp, a thin flexible wall, or a **slide/rotate after insertion**. |
| Retention | Positive: the barb bears on the sheet underside. Not friction. |
| Release | Needs a deliberate secondary motion (slide along, or flex the wall) — hence RockBoard ships a QuickRelease Tool. |
| Primary failure | Layer splitting across the thin hook wall — the author's README says "Print on edge otherwise the clips break", which is a layer-orientation warning, not a shape warning. |
| Secondary failure | Creep: a PETG barb held under preload relaxes at vehicle temperatures. |

## 4. The OEM QuickMount (vendor facts, mechanism inferred)

Vendor statements (Official, <https://www.rockboard.de/en/quickmounts/>):

- the plate is screwed to the pedal **using the pedal's own baseplate screws**,
  with longer screws supplied;
- it clicks into the **same slot grid** used for cable routing;
- removal needs the **QuickRelease Tool**;
- no permanent modification to the pedal.

Inferred from the above plus the reference parts: the OEM plate is a raised body
(the supplied longer screws prove a standoff) whose keeper is a **compliant
C-shaped arm** that snaps under the sheet and is pushed out of engagement by the
QuickRelease Tool. The compliance has to be large enough to let the barb pass the
slot opening, which is why the keeper is a C rather than a straight finger.

> Unconfirmed: the exact keeper travel, preload, contact area, retention force and
> cycle life. These need the physical plates in [inventory.md](inventory.md).

## 5. Design chosen for this project

Requirements behind the choice: printable in PETG by Kea Modelling, no supports on
mating faces, no reliance on spring compliance (PETG creeps), tolerance to a
±1 mm error in the provisional board dimensions, and simple hand operation.

**Chosen: two rigid hooks with a slide-to-latch motion.**

```
          pedal
   ┌───────────────────┐        plate, 3 mm PETG
   │  ○             ○  │        ○ = countersunk pedal screw
   │                   │
   │      ▼      ▼     │        hooks at ±33 mm, on a 2-pitch spacing
   └──────┬──────┬─────┘
          │      │              3 × 18 mm stems drop through two slots
        ┌─┴─┐  ┌─┴─┐            barb head, 6.5 mm, 45° underside ramp
        └───┘  └───┘
   ══════════════════════════   board: slot | rib | slot | rib
```

1. **Drop in.** The stems enter two slots 66 mm apart (2 × 33 mm pitch). The barbs
   pass through because the barb tip is 8.0 mm from the hook centre and the slot
   half-width is 10 mm.
2. **Slide 5 mm** along the pedal's depth. Each barb moves under the adjacent rib
   (3 mm of engagement), the stems stay inside their slots with 3.5 mm to spare.
3. **Lock.** The barb's upper face is 0.30 mm above the sheet underside, so the
   plate can only lift 0.3 mm before the barbs take load.

Why this shape: both barbs are rigid, so nothing depends on polymer spring
behaviour; the slide is a deliberate second motion, which is what makes it a lock
rather than a push-fit; and all the critical clearances are single numbers that a
single calliper reading can correct.

Known limitation (v0.1): nothing yet prevents the plate sliding back on its own.
That is acceptable while the pedal is loaded downwards, and the geometry is
arranged so the slide is against cable pull. A detent or a keeper screw is the
next iteration — tracked in `PLAN.md`.

## 6. Provisional board dimensions

| Parameter | Value used | Basis |
| --- | --- | --- |
| Slot width | 20.0 mm | inferred from pitch 33 − rib 13 |
| Rib width | 13.0 mm | mean of 12.5 / 14.3 from two independent clips |
| Pitch | 33.0 mm | clip spacing divided by slot count (33.25, 31.9, 38.3 observed) |
| Sheet thickness | 2.1 mm | 2.0 mm aluminium + 0.1 mm powder coat |
| Sheet top | datum (z = 0) | plate rests on the powder coat |

These are **provisional**. `catalog/boards/quad_4x.yaml` carries
`status: provisional`, and the manifest records it. Replace them with calliper
readings from the Quad and delete the flag:

1. slot width, measured across the short dimension with the inside jaws;
2. rib width between two adjacent slots;
3. pitch, slot centre to slot centre;
4. sheet thickness at the board edge with the micrometer.

Then re-run `python -m quickmount.build --step` and
`python -m quickmount.validate`. If the pitch differs, the hook spacing snaps to
the new whole number of pitches automatically.

## 7. Print orientation

The part must be printed **on edge** so the barb's locking face, which is
horizontal in use, becomes vertical on the bed:

- modelled in use coordinates (`z = 0` is the board-facing face, hooks at `z < 0`);
- exported rotated 180° about X, so the pedal face is on the bed and the hooks
  point up.

In that orientation the barb's locking face is a **downward-facing horizontal
shelf 5.4 mm above the bed** — a 6.5 × 18 mm overhang per hook, four in total.
Two options, in order of preference:

1. print on edge (rotate the STL 90° about X in the slicer) — no supports, but a
   3 mm × 122 mm footprint standing 66 mm tall, so use a brim;
2. print flat with supports under the two barb shelves only, "from buildplate
   only", in PETG, then skim the shelf with a sharp blade. The 0.30 mm latch
   clearance absorbs light marks.

## 8. Screw stack

The plate puts 3.0 mm between the pedal's baseplate and the screw head, and the
countersink recesses the head 1.55 mm, so the effective added length is
**1.45 mm**. Original screws are therefore usually 1–2 mm too short. See
[screws.md](screws.md) for the bill of materials.

## 9. Open items

| Item | Blocks | How to close |
| --- | --- | --- |
| Confirm the four board dimensions | Any real fit | Callipers on the Quad, §6 |
| Confirm pedal screw thread (M3 vs M3.5) | Screw order | Micrometer on a screw's major diameter |
| Retention vs the OEM plate | Acceptance test | Luggage scale, per [quickmount-system.md](quickmount-system.md#8-verification-protocol-per-design) |
| Anti-slide lock | Long-term security | Detent finger or keeper screw, next iteration |
| Whether the Quad's slot field matches Tres/Cinque | Board coverage | Borrow or measure a second board |

## 10. Sources

- RockBoard QuickMount overview: <https://www.rockboard.de/en/quickmounts/>
- RockBoard catalogue: <https://www.rockboard.de/downloads/RockBoard_Catalog.pdf>
- Reference clip models (CC BY-NC-SA, analysis only):
  <https://www.thingiverse.com/thing:6894147>
