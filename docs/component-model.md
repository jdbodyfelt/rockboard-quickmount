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

## 6. DigiTech Whammy IV draft

`catalog/pedals/digitech_whammy_iv.yaml` captures the supplied 200 × 203.2 mm
footprint, R6.35 corners, 4 mm plate, and four corner holes (Ø3.8 mm plain
clearance bores for #6-32 UNC screws). It sits to the right of the brown OC-2,
with its right edge aligned to the TU-3 tuner and both Velcro strips crossing
under the pedal, as shown in
[the placement photo](../reference/Cinque%20Captures/whammy_spot.jpg). In that
photo, +X runs right along the board and +Y points down across it; the plate
center is estimated at [+385, +96.5] mm from the board center. Its four clips
are aligned to openings visible in the photo; 17.7 mm clip width follows the
18 mm slots in [the Cinque 5.4 layout drawing](../reference/Cinque%20Captures/Cinque_54.jpg).
Clip spacing and center placement remain photo-derived estimates, not measured
coordinates, so test-fit on the physical board before use. The clip assemblies
are rotated 90° so their across-slot width follows the slot openings. The
recessed “Melting / Skies / DTW IV” stamp is rotated upright for the board view
with the pedal removed.

The supplied pedal spec places the rubber-foot centres about 15 mm from the
edges and the screw centres 8 mm from the edges, putting their centres about
10 mm apart diagonally. The feet are therefore assumed to cover the screws and
are to be removed; the mount has no foot pockets. The supplied #6-32 UNC fastener
specification calls for non-countersunk heads, so the four plate holes are plain
Ø3.8 mm FDM clearance bores. Either 1/4 in or 1/2 in under-head length is listed;
confirm the required thread engagement before assembly.
