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

## 3. What the reference clip actually is (measured)

The clip is a **constant cross-section extruded 16 mm across its width**. One
section contains two hooks joined by a flat bar. `catalog/clips/reference_2space_clip.yaml`
holds the measured polygon; the figures below are all taken from it.

```
                 arch            arch
              ______           ______
             /      \         /      \
   skirt  __|        |       |        |__  skirt
         |            \     /            |
         |             |   |             |
         +-------------+---+-------------+   bar
         |             |   |             |
         +-------------+---+-------------+
```

Measured features (bar underside taken as z = 9.18 in the file's own axis):

| Feature | Value |
| --- | --- |
| Overall width at the hook tips | 69.00 mm |
| Width across the bar | 35.40 mm |
| Bar thickness | **3.00 mm** |
| Clip width (extrusion) | 16.00 mm |
| Post thickness | 2.50 mm |
| Post height above the bar top | 7.00 mm |
| Arch wall thickness | 2.50 mm |
| Arch base to apex | 9.64 mm |
| Arch outer wall sphere, thinnest section | 1.20 mm |
| Lowest point below the bar underside | 19.64 mm |
| Hook centre lines | 32.90 mm apart (~ one 33 mm pitch) |

The 3.00 mm bar thickness is the important discovery: it is exactly the plate
thickness used by the author's own combined "Base + Clip" part. In that part the
bar has been replaced by the pedal baseplate, and only the hook section protrudes.
`Rockboard_Boss_Base_+_Clip` confirms it: a 61 x 116.5 plate with two hook
housings below it, 22.2 mm long and ~13 mm deep.

### 3.1 How it engages

Read as a mechanism, one hook is a **loop**: the post drops through a slot, the
arch springs outward and over the neighbouring rib, and the thin 1.20 mm skirt
descends on the far side. The two hooks are exactly one pitch apart, so they drop
into two adjacent slots and the bar spans the rib between them.

The loop is the spring: 1.20 mm of wall at the skirt gives it enough compliance to
pass the slot edge, while the 2.50 mm arch resists the pedal load.

### 3.2 What is still uncertain

The reference part is geometrically ambiguous about which face grips the sheet.
Measured gaps around the bar:

| Gap | Value |
| --- | --- |
| Bar top to inner skirt tip | 1.82 mm |
| Bar top to outer skirt tip | 4.00 mm |
| Sheet thickness (assumed) | 2.00–2.10 mm |

The 1.82 mm gap matches the sheet almost exactly, which suggests the sheet sits
between the bar's top face and the skirt's inner step. But then the 2.50 mm posts
would have to pass through the sheet, which is only possible at the slots — so the
geometry only works if the bar is **under** the sheet and the skirt presses on the
**top**.

That cannot be settled from the mesh alone. It needs one minute with the clip in
hand on a real board, and it is the single open question for the baseplate design.
Both orientations are supported in code:

- `mount_mode="bar_on_sheet"` — plate on the sheet, hooks below (the default, and
  what the author's combined Base + Clip part implies);
- `mount_mode="bar_under_sheet"` — bar under the sheet, hooks rising.

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

## 5. What this project builds

Only the mechanism, deliberately. Pedal-specific baseplates are out of scope until
the geometry is proven on a real board.

Three outputs, all from the measured cross-section:

| Part | Size | Purpose |
| --- | --- | --- |
| `out/keeper_ring.stl` | 18.3 x 16.0 x 19.64 mm | one C-shaped keeper ring: the unit |
| `out/keeper_arrangement_2ring.stl` | **69.1** x 16.0 x 19.64 mm | two rings on a bar, one pitch apart - matches the reference clip (69.0 mm) within 0.1 mm |
| `out/keeper_arrangement_3ring.stl` | 102.1 x 16.0 x 19.64 mm | three rings, two pitches - for a wider bar |

Each ring is a closed loop of the measured profile: a 2.50 mm post, a 2.50 mm
arch springing outward and over, and a 1.20 mm skirt returning down. The arch's
depth below the bar underside is 19.64 mm, and the ring's outward reach from the
bar end is 16.8 mm.

### 5.1 Arrangements

`build_arrangement(spec, rings=n, pitch=p)` lays `n` rings on a bar so that ring
centres are exactly `pitch` apart and the bar ends land on the post faces:

```
bar_len = pitch * (n - 1) + post_t
```

With the measured 32.90 mm reference spacing and a 2.50 mm post, n = 2 gives a
35.40 mm bar and the 69.0 mm overall width that the reference part has. Scaling
`pitch` to the board's slot pitch is the only coupling to the board, and it is a
single number.

The pitch is currently 33.0 mm from the board profile, so the two-ring arrangement
is 69.1 mm rather than the reference's 69.0 mm - a 0.1 mm difference, well inside
print tolerance.

### 5.2 Why no baseplate yet

A baseplate is just a bar with pedal screws in it, so it is a small extension once
the ring is proven. It is deliberately deferred because one question about the ring
is still open (section 3.2): which face grips the sheet. Printing the ring and
trying it on the Cinque answers that in a minute, and any baseplate built before
then risks being wrong again.

The housing data is already recorded for when it is needed: both target pedals are
vertical 125B and both take the OEM Type B1 plate
(`catalog/housings/125b_vertical.yaml`), so one measured screw pattern will serve
any pedal in that family.

## 6. Board dimensions

Target board: **RockBoard Cinque 5.2** (622 x 424 mm).

| Parameter | Value | Source | Status |
| --- | --- | --- | --- |
| Slot width | 17.7 mm | Callipers on the board, powder coat included | Measured |
| Rib width | **16.3 - 16.8 mm** | Micrometer, several ribs, powder coat included | Measured |
| Rib width, bare metal | 16 mm | Official Cinque 5.4 technical drawing ("16" punch-out) | Official |
| Pitch | **34.0 - 34.5 mm** (nominal 34.25) | Derived: slot + rib | Derived |
| Sheet thickness | 2.1 mm | 2.0 mm aluminium + 0.1 mm coat | Assumed |
| Under-sheet clearance | 22.0 mm | Estimate; must exceed the ring depth | Assumed |

The drawing's 16 mm and the micrometer's 16.3-16.8 mm agree once the powder coat is
accounted for: 16 mm of metal plus roughly 0.15-0.4 mm of coating per rib. The part
touches the coating, so **the coated numbers govern**.

### 6.1 The reference clip does not fit this board as-drawn

Two findings that invalidate copying the reference geometry unchanged:

| Problem | Numbers |
| --- | --- |
| Hook spacing too short | Reference 32.90 mm vs measured pitch 34.0-34.5 mm: **1.1-1.6 mm short** |
| Arch span has no margin | Reference arch span 16.8 mm vs rib **16.3-16.8 mm**: at the top of the rib range the skirt cannot enter the neighbouring slot at all |

So the arch is widened: the outboard part of the ring (everything beyond the post's
outer face) is scaled about that face until the arch span clears the **largest**
measured rib with a 1.2 mm intrusion:

```
target span = rib_max + 1.2 = 16.8 + 1.2 = 18.0 mm
scale       = 18.0 / 16.8   = 1.0714
```

The post keeps its 2.50 mm thickness because the scaling pivot is the post's outer
face. Only the arch reach and the skirt move. The ring goes from 19.30 mm to
20.50 mm of reach, and the two-ring arrangement from a nominal 69.0 mm to 72.75 mm.

Checks now enforced by `python -m quickmount.validate`:

| Check | Value |
| --- | --- |
| Skirt intrusion at the worst-case rib | 1.20 mm |
| Skirt still inside the slot at the smallest rib | 16.00 mm of room |
| Ring width vs slot | 16.0 in 17.7 = 0.85 mm per side |
| Pitch tolerance across two rings | ±0.25 mm, absorbed by the 0.85 mm per-side slack |

### 6.2 Remaining uncertainty

- **Pitch** is derived, not measured directly. Measuring slot-centre to slot-centre
  across four slots and dividing by four would remove the ±0.25 mm uncertainty.
- **Ring width.** 0.85 mm per side is looser than a locating fit. This is the
  reference part's own proportion and is flagged as a warning. `ring_width` is a
  parameter; if the printed ring rattles in the slot, 17.0 mm is the obvious value.
- **Sheet thickness and under-sheet clearance** are still assumptions.

### 6.1 What the official drawing does and does not give

`https://cdn.rockboard.de/nos/data/erp/Artikell_PDF/PDF_Drawing/RockBoard/Pedalboards/RBO_5.4_Technical-Drawing.pdf`

The drawing is a vector CAD export with all text converted to outlines, so nothing
is machine-readable. Measured and read visually, its callouts cover the envelope
(1002 mm length), frame and hinge details, feet (4x Ø11, 4x Ø7), and the above
16 mm rib. **It does not dimension the slot width, slot length, or the sheet
thickness.** Slot width therefore still rests on callipers.

Note: the four `reference/cinque_54_00*.pdf` files are Thomann product pages, not
drawings - they contain no technical content.

## 7. Print orientation

- the clip and the plates are modelled with the plate on top and the hooks below;
- print them **as exported**: plate face down on the bed, hooks rising.

That makes each hook an upright loop: the arch becomes a vertical arch and the
descending skirt becomes a vertical wall, so every filament runs along the load
path. This is what the reference author means by "print on edge otherwise the
clips break".

The only overhang is the underside of the arch's outer return, a short 45-60 deg
region at the top of each loop. No supports; use a brim on the plates.

## 8. Screw stack

The plate puts 3.0 mm between the pedal's baseplate and the screw head, and the
countersink recesses the head 1.55 mm, so the effective added length is
**1.45 mm**. Original screws are therefore usually 1–2 mm too short. See
[screws.md](screws.md) for the bill of materials.

## 9. Open items

| Item | Blocks | How to close |
| --- | --- | --- |
| Which face grips the sheet (§3.2) | Final baseplate orientation | Print `clip_reference_2space.stl`, try it on the Cinque 5.2 |
| Confirm the four board dimensions | Any real fit | Callipers on the Cinque 5.2, §6 |
| Confirm pedal screw thread (M3 vs M3.5) | Screw order | Micrometer on a screw's major diameter |
| Retention vs the OEM plate | Acceptance test | Luggage scale, per [quickmount-system.md](quickmount-system.md#8-verification-protocol-per-design) |
| Two hook lines vs one | Pedal stability | First printed article |
| Whether the Cinque's slot field matches Tres/Quad/Duo | Board coverage | Borrow or measure a second board |

## 10. Sources

- RockBoard QuickMount overview: <https://www.rockboard.de/en/quickmounts/>
- RockBoard catalogue: <https://www.rockboard.de/downloads/RockBoard_Catalog.pdf>
- Reference clip models (CC BY-NC-SA, analysis only):
  <https://www.thingiverse.com/thing:6894147>
