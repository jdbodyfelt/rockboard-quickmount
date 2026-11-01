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

Two parts are generated:

1. **The clip, reproduced.** `out/clip_reference_2space.stl` is the measured
   section extruded 16 mm, i.e. the reference clip itself, 69.0 x 16.0 x 19.64 mm,
   within 0.6 % of the original volume. Print this first and test it on the board:
   it answers the orientation question in §3.2 without any CAD risk.

2. **A baseplate per pedal, carrying that same hook section.**
   `out/<pedal>__cinque_5_2__petg__*.stl` is the pedal footprint, 3 mm thick, with
   four countersunk pedal screws and the reference hook section under it at two
   stations. The bar is absorbed by the plate because both are 3.00 mm thick, so
   only the hook geometry protrudes.

Differences from the reference part, and why:

| Change | Reason |
| --- | --- |
| Hook section scaled 1.003x in X | Puts the hook centres exactly one slot pitch apart for the target board instead of the reference's 32.90 mm |
| Two hook lines instead of one | The reference clip is a single line; a 120 mm pedal needs support at both ends |
| Bar replaced by the pedal plate | Same thing the author does in `Rockboard_Boss_Base_+_Clip` |
| Countersunk pedal screws added | The pedal's original baseplate screws hold the plate on |

Everything else - post thickness, arch wall, skirt thickness, arch depth, overall
width - is taken unchanged from the measurement.

## 6. Provisional board dimensions

Target board: **RockBoard Cinque 5.2** (622 x 424 mm, 3.95 kg - envelope from the
RockBoard catalogue).

| Parameter | Value used | Basis |
| --- | --- | --- |
| Slot width | 20.0 mm | inferred from pitch 33 - rib 13 |
| Rib width | 13.0 mm | 12.5 and 14.3 measured on two independent reference clips |
| Pitch | 33.0 mm | reference hook spacing 32.90 mm; other clips imply 31.9 and 38.3 |
| Sheet thickness | 2.1 mm | 2.0 mm aluminium + 0.1 mm powder coat |
| Under-sheet clearance | 22.0 mm | estimate; must exceed the 19.64 mm hook depth |

These are **provisional**. `catalog/boards/cinque_5_2.yaml` carries
`status: provisional` and the manifest records it. Replace them with four calliper
readings and delete the flag:

1. slot width, across the short dimension with the inside jaws;
2. rib width between two adjacent slots;
3. pitch, slot centre to slot centre;
4. sheet thickness at the board edge with the micrometer.

Then `python -m quickmount.build --step` and `python -m quickmount.validate`. The
hook spacing rescales to the new pitch automatically; the hook depth is fixed by
the reference geometry, so check it against the measured under-sheet clearance.

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
