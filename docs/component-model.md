# Component model

A QuickMount-compatible plate solves two independent attachment problems. Keeping
them apart in code is what makes a generator possible, because each one has its own
parameters, its own validation, and its own failure mode.

| Component | Attaches to | Geometry | Parameters |
| --- | --- | --- | --- |
| **Clip** | one board slot | one C-shaped keeper ring: post, arch, skirt | profile (measured), arch scale, width across the slot |
| **Spine** | the slot grid | 1..n clips strung along an axis, plus a bar joining them | clip count, post spacing (= slot pitch), axis, flare direction, plate clearance |
| **Wing** | the pedal | plate or beam surfaces | outline, thickness |
| **Mount hole** | the pedal | clearance bore, optionally with a 90° countersink | position, bore, optional countersink diameter and face |
| **Retainer column** | the pedal | vertical post with a lip | position, height, thickness, depth, lip, facing |
| **Brand stamp** | mount identity | two-line recessed text on the flat pedal-facing surface | fixed company name, model number, position, font, depth, rotation |

```
        plan view                          section through a spine

   ┌─────────────── wing ───────────────┐        pedal face  z = 0
   │  ○                             ○   │      ══════════════════════  plate
   │        ▓▓▓  spine  ▓▓▓            │            ▓ │       │ ▓   board face
   │        ▓ ░ ░ ░ ░ ▓                 │            ▓ │       │ ▓
   │  ○     ▓  clips  ▓             ○   │            ▓ └───────┘ ▓   clips
   └───────────────────────────────────┘            ▓             ▓
        ○ = mount hole      ▓ = clip, ░ = clearance notch
```

## 1. The spine is the board attachment

A spine is an axial arrangement of clips. It is not "the plate with hooks on it";
it is a beam carrying clips, and the plate is what grows out of it.

Three knobs cover every OEM arrangement seen so far:

- **`clips`** — one for a single-row mount, two for the 125B, three for a wide bar.
- **`axis`** — the direction the clips are spaced along, which is also the direction
  the arches flare. Point it **across** the board slots to engage two slot rows
  (the 125B case), or **along** the slots for a single-row mount that spans one or
  two ribs (the wah-style Type M case).
- **`flare`** — `outward` puts the clips at the ends of the spine flaring away from
  its centre (the 125B); `inline` points every arch the same way, reproducing the
  reference 2-space clip.

`along_offset` shifts the whole clip row along `axis`. The default 0 centres it;
a single clip with `along_offset: 38.1` sits one slot row up, which lets a split
plate keep one clip per spine while preserving the mirrored flare of the full
plate's upper clip.

`post_spacing` is measured post face to post face and must equal the board's slot
pitch: that one number is the whole coupling between the mount and the board.

### Clearance

Each clip needs open plate behind its arch so the skirt can flex outward when the
lip passes the slot edge. `build_mount` cuts that notch from the post's outer face
outward, through the arch reach plus the configured clearance. Optional
`clearance_width` and `clearance_radius` values widen the notch and round its
inner corners; the measured 125B uses a 24 mm-wide notch with 6 mm inner radii.
The cut preserves the plate land beneath the full post. That notch is what you
can see either side of the spine, and getting it wrong is the difference between
a clip that springs and one that cannot.

### One or two spines

`MountSpec.spines` is a tuple, so a mount can carry:

- one spine for a compact pedal (125B, Strymon-style side plates);
- two parallel spines for a large pedal, e.g. left and right edges (Strymon v1/v2)
  or top and bottom (wah plates);
- two perpendicular spines is possible but has no OEM precedent — treat it as a
  test case, not a default.

The Line 6 modeler config keeps its 254 × 152 mm pedal footprint in the source
spec orientation while setting the clip spines across the board's longitudinal
slots. This rotates the board-clip layout relative to the pedal; it does not
rotate both together. The 76.2 mm clip spacing and ±45 mm spine locations remain
unverified assumptions until checked against the Cinque 5.2 slot-centre matrix.

## 2. The wing is the pedal attachment

Wings are the surfaces that reach the pedal, and they come in two flavours:

- **mount holes** — a clearance bore, optionally countersunk, matching the
  pedal's baseplate screws. Where a countersink is used, it opens on the
  **board** face, i.e. the same face the clips are on, so the screw head is flush
  where the board is and the pedal sits on the plain face.
- **retainer columns** — vertical posts with a lip that catch the sides of a pedal
  with no baseplate holes (solid-case pedals, Type G). These do not need
  countersinks because nothing is screwed through them.

A mount can mix both: screw holes at one end, a column at the other, for pedals
whose baseplate only has two screws.

### Pockets and lightening

A wing does not have to be solid. `WingSpec.pockets` cuts after the plate is
extruded, and each pocket is either `through` or blind on a named `face`:
`pedal` opens on the pedal-facing surface at z = 0, `board` opens on the clip side
at z = thickness. The Whammy V uses four blind `pedal`-face pockets so its stock
rubber feet sit in recesses instead of being removed; each pocket clears the
11 mm foot base by 0.6 mm and is 2.8 mm deep for the 2.5 mm foot, leaving a
1.2 mm floor.

Through-windows are the other option for a plate much larger than its fasteners:
cut the dead area away and keep a uniform frame. Whichever is used, keep each cut
clear of the clip post land and the screw boss, and round its corners so the load
path has no sharp internal corner. For the Whammy the plate outline is driven by
the pedal's measured footprint, so any lightening is deferred until the edge-finger
retention is laid out.

## 3. The brand stamp

An optional `BrandStamp` component engraves **Melting**, **Skies**, and the
configured model number on separate lines, with an additional gap before the
model. It is cut into the flat pedal-facing face so it can be epoxy-filled for
contrast. Position, font size, font (including a bundled font file), line
spacing, model gap, depth, and rotation are configurable. The 125B stamp uses
the bundled Google Font Lacquer at 9.5 mm, with a 0.2 mm vector-outline
expansion to give the regular-weight font a bold appearance. The longest line
spans 32.5 mm, centered within the middle half of the plate's 65 mm short edge.
The stamp is rotated so its text baselines follow that edge, and is recessed
0.4 mm. The font can be changed in the YAML configuration; Tac One, Aclonica,
and Irish Grover are other candidate Google Fonts.
The lettering outlines are mirrored in the CAD plane so they read normally
when viewed from the pedal-facing side of the mount.
Two rounded frame outlines are engraved at the same depth: one surrounds both
company lines, and the other surrounds the model number. Their padding (2.5 mm
on the 125B, leaving 1.7 mm from the lettering to the frame's inner edge),
stroke width, and corner radius are configurable through the stamp component.

The original Type E blueprint specifies a 120 × 65 mm plate with 3 mm
thickness, matching the 125B model. The supplied foam/rubber mat sits on the
board-facing side, between the plate and the RockBoard top; it is an accessory,
not part of the plate solid. The measured keeper profile has a 3 mm skirt from
z=7 to z=10 mm, with the plate spanning z=0 to z=3 mm. With a 3 mm board sheet
and a 3–4 mm mat, the sheet occupies z=6–9 or z=7–10 mm respectively, giving
about 2–3 mm of overlap with the skirt. This matches the OEM stack-up
geometrically; actual retention still depends on the mat's compressed
thickness and should be checked on the board. The 0.4 mm brand engraving is on
the opposite, pedal-facing surface and leaves 2.6 mm of plate beneath it.

## 4. The 125B, read as components

`catalog/pedals/125b_quickmount.yaml` is the measured reference part expressed this
way, and `python -m quickmount.mount` rebuilds it:

| Component | Measured value |
| --- | --- |
| plate thickness | 3.0 mm |
| plate outline | 120 × 65 mm, R3 corners |
| spine | 2 clips, X axis (across the slots), posts 76.2 mm apart |
| clip width | 22.0 mm across the slot |
| clip centre | 11 mm off the plate centre, along Y |
| mount holes | (±55.6, −17.6) and (±55.6, +39.6) |
| hole | Ø3.7 bore, Ø6.7 × 90° countersink on the board face |
| brand stamp | “Melting” / “Skies” / “125B”, 0.4 mm recess on the pedal face |

## 5. Open questions this model exposed

1. **Clip width vs slot width.** The OEM clips measure 22.0 mm across, but
   `catalog/boards/cinque_5_2.yaml` carries a provisional slot width of 17.7 mm. A
   22 mm clip cannot enter a 17.7 mm slot, so the provisional board number is
   wrong. Measure the real slot.
2. **Post spacing vs pitch.** The OEM posts are 76.2 mm apart against a provisional
   board pitch of 34.25 mm. Either the pitch is wrong or this part deliberately
   engages slots two rows apart.
3. **Wing outline for other pedals.** The 125B is a full rectangle because its
   four screws sit near the corners. A pedal with a narrow baseplate needs the
   wing trimmed back to a beam, which is a per-pedal outline, not a new component.

Both board numbers are marked provisional in the board profile. Neither should be
treated as settled until the Cinque is measured with callipers.

## 6. DigiTech Whammy V draft

`catalog/pedals/digitech_whammy_v.yaml` is built from the owner's own
measurements of the physical pedal (2026-11-03), not from a supplied drawing.

| Feature | Measured |
| --- | --- |
| Envelope | 165.0 × 197.0 mm (published 165 × 197; owner callipers read 163 × 195) |
| Corners | square — the lower shell is a stamped and bent sheet, not a filleted casting |
| Lower shell | full sheet, folded up on the left, right and rear sides; the front is open |
| Upper assembly | front and top are a second piece, bolted with five black hex-head screws |
| Feet | 4, one per corner; Ø11 base, Ø10 flat contact face, 2.5 mm high, no metal cup |
| Foot inset | 15.5 mm from the left, right and rear edges; 18 mm from the front |

Retention is by **edge fingers** that hook the side wall and bear on the five
hex-head screws, not by screws through the plate. The four corner mounting holes
in the earlier draft came from an unverified 200 × 203.2 mm drawing and cannot
exist on a 165 mm width, so `mount_holes` is empty.

The plate is 165 × 197 mm, 4 mm thick, with four blind recesses on the pedal face
for the stock rubber feet, which stay fitted. Each recess clears the 11 mm foot
base by 0.6 mm and is 2.8 mm deep against the 2.5 mm foot, leaving 1.2 mm of
material beneath.

The clips are placed from the board outward rather than from the pedal inward. A
keeper arch straddles a **rib**, and on RockBoard the slots (and therefore the
ribs) run along the board's long axis, so the arch reaches across the board in
+Y. That fixes the spine axis to Y, and it means clip centres must sit on rib
centres — so their separation has to be a whole number of slot pitches. The
Whammy uses 3 × 34.0 = 102.0 mm post-face to post-face, putting the pair ±51 mm
across the plate, with the two spines 110 mm apart along +X so the plate cannot
rock about either axis. The superseded draft's 76.2 mm spacing was 2.24 pitches,
which cannot land on the grid at all.

The plate's position on the board is **measured, not estimated**: on the actual
Cinque 5.4 the pedal's lower face and right face sit flush against the board's
lower and right edges. With a 1002 × 424 board and a 165 × 197 pedal, that puts
the plate centre at [+418.5, +113.5] mm and the four clips at board coordinates
(363.5, 62.5), (363.5, 164.5), (473.5, 62.5) and (473.5, 164.5).

Still open:

1. **Rib phase.** The clip rows land 47.5 and 149.5 mm from the board's lower edge
   on the bare geometry. Ribs repeat every 34.0 mm, and the official drawing's
   424 mm board with a 394 mm slot field implies a 15 mm edge margin and a first
   rib centre at 15 + 18 + 8 = 41 mm; the owner reads ~45 mm on the board. The
   clip row carries `along_offset_mm: 2.5` to sit on 45 and 147 mm. If calipers
   say 41, the row moves another 4 mm and the front clip's flex notch reaches
   76.3 mm, into the front foot recess at 74.7 mm — that case needs either 2-pitch
   clip spacing or a shallower foot pocket. As built, the ligament between those
   two cuts is 2.4 mm.
2. **Slot spans.** The clip columns are 27.5 and 137.5 mm from the board's right
   edge. Slots are 60 mm or 98 mm long and staggered, so confirm both columns fall
   inside a slot opening rather than across a slot end.
3. **Board edge lip.** The plate copies the pedal footprint exactly, so flush to
   the board's right edge its edge reaches the board's folded edge. Check the lip
   does not hold the plate off the sheet.
4. **Slot width.** The clip is 17.7 mm wide, the measured Cinque 5.2 slot width,
   against 18 mm on the official 5.4 drawing.
5. **Side wall.** The wall's top edge is a "Z": it slopes front to rear and steps
   where the rocker pedal starts, the front and rear ends are slanted, and there
   is a row of 14 mm ear-cut notches where the mount ears were bent. The manual's
   plan and elevations, rescaled to 165 × 197 and 197 mm wide respectively, give
   a wall top edge that falls about 4 mm over 114 mm (roughly 2°) and steps near
   the front, but the sketch cannot resolve the notches or the step, so those
   need micrometer values before the fingers are drawn.
