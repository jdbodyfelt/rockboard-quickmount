# Step-up and riser geometry review

Reviewed 2026-11-07 against the six sheets copied into `ref/` from
`commons/ref/stepups/`. Units are mm. Provenance follows the repo's levels: 3 is
a printed or officially drawn dimension, 2 is a vendor page, 4 is measured.

The PedalRiser was re-read on 2026-11-14 and its anatomy, its 121.0 reference and
its sheet thickness are corrected below. `src/pedal_riser.py` is that re-read as a
solid: 33 checks against the sheet's own callouts, `dwg/pedal_riser.stl` and
`.step`. Nothing else on the sheet needed to move.

## The family splits in two

| Unit | Top | Takes a QuickMount plate? | Envelope |
| --- | --- | --- | --- |
| StepUp-1 | plain, 4 x Ø9.5 | no | 90.0 x 142.5 x 25.0 |
| StepUp-2 | plain, 4 x Ø9.5 per cell + 1 x Ø31.5 | no | 180.0 x 142.5 x 25.0 |
| StepUp-3 | plain, 4 x Ø9.5 per cell + 2 x Ø31.5 | no | 255.0 x 142.5 x 25.0 |
| PedalRiser | slot field, 18 wide, 76.0 clear | **yes** | 135.0 x 76.0 x 41.0 metal, 46.0 over its pads |
| PedalRiser-L | slot field, 18 wide, 98 long | **yes** | 212.0 x 134.5 x (open) |
| SecondTier-Tier2S | full board-style slot field | **yes** | 150 x 320 x 85 |

This is the finding that sets the printed design: the units with the board's
slotting on top are the three risers, not the three Step Ups. So the printed part
borrows the Step Up's 25 mm envelope and the PedalRiser's slotted top.

## StepUp-1/2/3 anatomy

All three are one 1 mm bent steel sheet, and share one cross-section:

- Depth **142.50** (printed on the section). A published 145 for StepUp-1 is
  superseded: the sheet prints 142.50.
- Length **90.0 / 180.0 / 255.0** = 1 / 2 / 3 cells at 90.0 pitch.
- Height **25.01** at the front wall, **25.00** at the rear. The top is level;
  the 9° callout is the folded foot, not a sloping deck.
- Front: a full-height wall folded down, then a **25.00** foot turned inboard at
  9° above horizontal. R2.00 at the fold.
- Rear: the sheet turns under with **R1.50** into a **25.00** hem, 1.00 thick.
- R3.00 on the plan corners.
- Each 90 cell carries 4 x **Ø9.5** holes at **12.75** from the fold and **13.25**
  from the side, and a **Ø31.50** hole sits between adjacent cells (1 on StepUp-2,
  2 on StepUp-3, none on StepUp-1), 71.25 in from the front and 89.00 apart on
  StepUp-3.

The topology is a shelf: a raised deck carried by one wall at the front and a
stiffening hem at the rear, open underneath. That cannot carry the retainers a
QuickMount plate needs, which is why it is a reference for the envelope only.

## PedalRiser anatomy

Re-read 2026-11-14, because the first pass took 121.0 for the envelope length.
`src/pedal_riser.py` now reproduces the sheet as a solid and its 33 checks hold
these numbers; this section records what each one is.

- One **2.0** steel sheet, not 1.0 and not aluminium: its edge reads 8 px on the
  front wall and again on the front flange against 474 px for 121.0, so 2.04 mm,
  and PedalRiser-L's title block prints "material: steel, 2,0 mm powdercoated
  black". The Step Up kits are the 1.0 family.
- Length **135.0**, width **76.0**. The 135.0 is not printed: it is the printed
  121.0 plus the printed 12.0 lip station plus the 2.0 sheet, and the raster
  measures 135.0 against its own dimensions.
- Front wall **20.0** and rear wall **41.0**, both printed, both measured to the
  top corner at the end face. Both to the metal's underside, so the part stands
  46.0 on its 5.0 pads. The deck plane between the corners falls at
  atan(21 / 135) = **8.84 deg**; the drawn plane fits at 8.97 +/- 0.15, which is
  the same angle inside a raster's accuracy.
- A **22.0** foot turned inboard at each end, printed on the bottom view, so 20.0
  of flange stands inboard of the wall's inner face. Under each foot: two **Ø18 x
  5.0** rubber pads, 12.0 in from the end face and 11.5 in from each side edge.
- Deck: two slots **18.0** wide and **60.0** long, R4 ends, cut square to the deck
  so each is truly 18.0 for a retainer, with **76.0 clear** between them in plan
  and **min. 8.0** of deck to each side edge. That is the board's own vocabulary -
  18 slot, R4 end - reduced to two groups, and 76 = 8 + 60 + 8 is what fixes the
  slot length, which the sheet does not print.
- Each end wall is interrupted by a centre gap **33.0** wide whose top stands 6.0
  below the deck's edge, so **35.0** above the feet at the rear and 14.0 at the
  front by the same rule. That leaves a leg 21.5 wide at each corner, with the
  foot carried across the gap.
- **121.0** is a reference, not the length and not a height: on the 135.0 part it
  is 135.0 - 12.0 - 2.0, the front lip station to the rear wall's inner face. On
  PedalRiser-L the same callout is 134.5 - 12.0 - 2.0 = 120.5. It is also a
  standard pedal's length, so it reads as the footprint the riser is meant to
  clear, which would be why both sheets carry it.
- Not reproduced, and called out in `cfg/pedal_riser.json`: a 24.0 wide tongue
  hanging 3.0 below the front foot, the step-back of the foot between the pads,
  and the bend radii (so 20.0 and 41.0 read exactly, where a real R1.3 bend would
  take about 0.4 off a calipered 41.0).

PedalRiser-L is the same idea in 2 mm steel on a 228.0 base; its underside view
repeats the 98 / 16 / R4 slot field.

The 76.0 between the two slots is **not** a rib pair: it is a clear span, so the
two slot centres land 94.0 apart, which is 1.0 inside the B1 plate's 95.0 clip
pair. Whether a plate actually rides them is a check to run, not a given.

## What that means for a printed riser

The printed risers in `src/stepup_riser.py` are one part that does both jobs, in
the Step Up's form: front leg, sloped deck, rear leg, on a 3 mm base plate.

**Deck.** A sheet carrying the board's slot field so a QuickMount plate drops on.
The field is the Cinque grid: **18.0** slots, **16.0** ribs, **R4** ends, with the
ribs set either to a 34.0 pitch (generic) or to a target plate's clip centres
(dedicated). The retainer mouth is 13.0, so a 16.0 rib is a 3.0 squeeze, 1.5 a
side, which is the same interference the board gives. The slots are cut square to
the deck's own plane, so each one is a true 18 wide for the retainer even though
its plan width is 18 x cos(slope).

The sheet is **4.0** thick, not the board's 3.0. The retainer's ledge sits 4.0
below the pedal plate's underside; on the board that gap is closed by a 1 mm foam
pad. A 4.0 sheet closes it directly, so the plate grips flush on the riser without
a pad. This is the only dimension deliberately taken off the board spec.

**Bottom.** A 3.0 plate with two integral C-loops. The section is read from
`commons/cfg/retainer.json`; the construction copies the Type B1 plate: the post
fuses into the plate, the blade stands in a window, the ledge stays free. Because
the clips sit inside the footprint rather than at an end edge, the B1 end window
is closed off outboard into a 24.6 x 21.9 rounded opening whose inboard wall lands
on the mouth wall, exactly as on B1.

The clips are **102.0** apart = 3 x 34.0, so both land on ribs of the board.

**Body.** The Step Up's own silhouette: a front leg, a sloped deck and a rear leg,
standing on the base plate. The deck is a plane, so the whole body is one prism
with a sloped top, dug out to a 3.0 perimeter and filled with ribs; each rib is
clipped by that prism, so it stops on the deck's underside at its own height
instead of all of them reaching one flat ceiling. The retainer keep-outs are cut
from the finished part, square to the deck.

**Height.** The deck has to be high enough that the pedal plate's retainer, hanging
from the deck's top face, clears the base plate. The low edge therefore stands
`base 3.0 + clearance 3.0 + loop drop 15.89 = 21.89`; the slope then lifts the high
edge by `depth x tan(slope)`. At 9 deg over 172 that gives 21.89 low and **49.13**
high - within 0.3 of the 49 that PedalRiser-L's own section prints, which is the
corroboration for using the retainer drop as the driver.

That is why a slanted step-up is much taller than the level Step Up's 25.01: at 25
there is only 1 deg of slope available before the low edge drops below the
retainer. `deck_slope_deg: 0` in the config collapses it back to a level deck at
that same low height.

**Print.** Base plate on the bed, the deck rising last. The clip loops overhang and
want supports; the mouths stay open with no bridging, and the deck's slots print as
short horizontal bridges.

## Two instances

| Config | Envelope | Deck | Top | Clips |
| --- | --- | --- | --- | --- |
| `cfg/riser_two_125b.json` | 180 x 172 | 21.89 low to 49.13 high at 9 deg | 8 slots; ribs at ±47.5, the B1 clip centres | ±51, 102 apart |
| `cfg/riser_line6_modeler.json` | 264 x 176 | 21.89 low to 49.77 high at 9 deg | 15 slots on a true 34.0 grid; ribs at ±17, ±51 | ±51, 102 apart |

The two-125B deck is 172 deep rather than the Step Up's 142.5 because the outer
slot edge falls at 73.5 either side of the B1 clip line; 142.5 leaves no flange.

## The single-125B base

The second riser line starts from the other reference: `enclosure_125b`'s Type B1
plate rather than the Step Up plan. `cfg/single_125b.json` points at that plate's
config, so the outline (125.5 x 72 x 3, 67 between the straight sides, r 6.6 lobes
about the snap holes, r 4.5 bosses on the side holes) and its three screw patterns
are read in, not restated.

What is removed is the board-side attachment: both integral C-loops, and with them
the 24.6 x 21.9 end window, which is cut through and open to the end edge for no
other reason than to let the clip's blade stand free. The part that prints is
therefore a plain lobed plate - the pedal's own fasteners, a flat board face, solid
ends - and `dwg/single_125b_base.stl` is that plate alone.

This is step one, not a finished riser. The base has no board-side grip of its own
yet, and the attachments it could take are the open question below: integral loops
hung under this outline, the way `riser_two_125b` does it, or the separate printed
retainer of `commons/src/retainer.py` seated in a closed window.

## The layout check

`src/riser_check.py` answers the question the two references raise: where does the
single-125B riser sit between a StepUp-1 and a PedalRiser? It puts four bodies on
one board surface - the board strip, the whole B1 plate on it, the clip-free
`single_125b` base laid on the plate and tilted about its front edge, and the two
reference products either side - and writes them as `dwg/riser-check.stl`.

| On the board | Footprint | Height | Deck |
| --- | --- | --- | --- |
| 125B stack | 72.0 x 125.5 | **26.60** | 9 deg, falling to the front |
| StepUp-1 | 90.0 x 142.5 | 25.01 | level |
| PedalRiser | 76.0 x 121.0 | 41.00 | 9 deg, falling to the front |

The PedalRiser row is still the check's own stand-in, which is 121.0 deep by
41.0 high. The reference product is **135.0 x 76.0**, 41.0 of metal and 46.0 off
the board on its pads, falling at 8.84 deg - see `src/pedal_riser.py`. That is
1.0 deg and 14 mm of footprint apart from the stand-in, so read this table as the
comparison the check draws, not as the reference's envelope.

So the stack lands a little above a StepUp-1's level top and well under a
PedalRiser's rear: a StepUp's height class with a PedalRiser's slope. It is one
pedal wide because a 125B is 67 x 121, against the StepUp-1's 90 x 142.5 cell.

Two things come out of the check that the numbers alone do not show.

**The plate stands 1.00 above the board, not on it.** The clip's ledge is 4.00 below
the plate underside and catches the board's underside, so with a 3.0 sheet the plate
underside is `4.00 - 3.00 = 1.00` clear of the board's top face and the loop hangs
11.89 past the sheet. Any body added under the deck has to leave that gap.

**The board is phased for one clip only.** With the strip's ribs 34.0 apart and one
rib centred under the +Y clip, the -Y clip lands 7.00 off the nearest rib, so its
13.0 mouth sits inside a 16.0 rib instead of gripping it. 95.0 is 2.79 pitches: the
pair cannot both grip, whichever way the board is phased. That is open item 3, now
demonstrated rather than described.

The PedalRiser in the check is an envelope stand-in. The sheet it stands in for is
a raster with no text layer, but it has since been read by eye against its own
dimensions and reproduced in `src/pedal_riser.py`, which is what the numbers above
come from; the check itself still draws the stand-in, so its silhouette is 121 deep
at 9 deg rather than 135 at 8.84. The StepUp-1 is built from its own printed
callouts.

## Open items

1. The 9 deg deck of the printed risers is a design choice, not a measurement:
   StepUp-2's own top is level, so the wedge is PedalRiser's idea applied to the
   Step Up plan. The reference falls at 8.84 deg, so 9 deg is within 0.2 of it;
   confirm the angle against how the pedals need to sit, then set
   `deck_slope_deg`.
2. Answered 2026-11-14: the PedalRiser's 76.0 is the clear span between two 18.0
   slots, not a group pitch, and the slots are 60.0 long because the 76.0 width
   leaves min. 8.0 at each side edge. The remaining question is whether a QuickMount
   plate's clip pair lands on them: the two slot centres are 94.0 apart against the
   B1 plate's 95.0, so caliper that 1.0 before trusting it.
3. The B1 plate's own clips are 95.0 apart, not a multiple of 34.0, so on a real
   board the pair cannot both sit on ribs. The two-125B riser sidesteps this on its
   own underside but inherits the same problem from the pedal plate above it; print
   a first article and check the grip.
4. No QuickMount type covers the modeler chassis, so its deck is a generic grid
   until a modeler plate is generated.
5. The 125B stack's deck is a bare plate tilted on the B1 plate: nothing fills the
   wedge, holds the rear edge up, or lifts the front edge clear of the base plate's
   fastener field. That body is the next step, and `riser-check.stl` is the drawing
   it has to fit.
6. Whatever fills the wedge has to solve the mount screws, and the geometry of that
   is not obvious from the plate: a pedal's screws come **up** from under its plate,
   and the B1 pattern's Ø6.8 head recesses are on the board face - so on a riser the
   heads sit inside the wedge with the deck above them. The deck resting on the
   B1 plate leaves the front row 0.94 of headroom against the 3.5 a head and its
   recess need. Any body that arrives has to answer this before it is drawn.
7. The honeycomb is sized for the body, not for load: no grid here proves the wedge
   under a stomped pedal.
