# Screw bill of materials

What to order so the printed plates can be fitted to the Tumnus Deluxe and Mira,
and why.

## 1. The problem

The pedal's baseplate screws clamp the pedal's own metal bottom plate. Adding a
3.0 mm printed plate under the pedal moves the screw head 3.0 mm further from the
thread, minus the countersink:

```
effective added length = t_plate - countersink_depth
                       = 3.00 mm - 1.55 mm = 1.45 mm
```

So the original screws need roughly **1.5 mm more length**, and the printed plate
must also be clamped hard enough not to creep. Reuse the originals only if they
still engage at least 4 mm of thread.

## 2. Which thread size

The measured countersunk head OD is **6.5 mm**. Standard 90° countersunk (DIN 965
/ ISO 7046) head diameters are:

| Thread | Head Ø | Matches 6.5 mm? |
| --- | --- | --- |
| M3 | 5.6 mm | no — 0.9 mm small |
| **M3.5** | **6.5 mm** | **yes** |
| M4 | 7.5 mm | no — 1.0 mm large |

So **M3.5 is the most likely thread**, which is common on pedal baseplates. Confirm
before ordering by measuring a screw's major diameter with the caliper:

| Thread | Major diameter you should read |
| --- | --- |
| M3 | 2.87 – 2.98 mm |
| M3.5 | 3.35 – 3.48 mm |
| M4 | 3.84 – 3.98 mm |

The plate's through hole is 3.8 mm with a 6.7 mm × 90° countersink, so both M3 and
M3.5 countersunk screws seat correctly — M3 simply sits a little deeper. That is
deliberate: it means the plates are usable whichever thread the pedals turn out to
use.

## 3. Order list (AliExpress)

Search terms are given as they appear on AliExpress; add `304 stainless` and
`DIN965` or `ISO7046` to most listings.

| # | Item | Search term | Qty | Why |
| --- | --- | --- | --- | --- |
| 1 | **M3.5 × 10 countersunk** | `M3.5 countersunk head machine screw 90 degree DIN965 304 stainless` | 20 | primary candidate; +1.5 mm over a typical M3.5 × 8 |
| 2 | **M3.5 × 12 countersunk** | `M3.5x12 countersunk flat head screw DIN965 stainless` | 20 | if the pedal's screws are 10 mm or the thread is deep |
| 3 | **M3 × 10 countersunk** | `M3 countersunk head screw DIN965 304 stainless` | 20 | fallback if the thread measures M3 |
| 4 | **M3 × 12 countersunk** | `M3x12 countersunk screw DIN965 stainless` | 20 | fallback, longer |
| 5 | **Assorted M3/M3.5/M4 countersunk kit** | `M3 M4 countersunk screw assortment box stainless` | 1 box | certainty: one box covers all cases for a few dollars |
| 6 | Thread pitch gauge (optional) | `metric thread pitch gauge tool` | 1 | confirms size without guessing |
| 7 | Thread checker plate (optional) | `screw thread checker M3 M4 M5 metric` | 1 | fastest way to identify the baseplate screws |

Buy items 1–4 in **304 (A2) stainless** so the heads do not rust into the pedal.
Avoid 316 if you might ever use threadlocker (it reacts badly); 304 is fine.

Order the **assortment box (item 5)** if you only want to buy once — it removes the
guesswork entirely and costs little more than two single-size packs.

## 4. Fitting notes

1. Check thread engagement before tightening: with the plate fitted and the screw
   finger-tight, there must still be thread left. If a screw bottoms out, it is
   too long — go down one length, never force it (there is a PCB under the
   baseplate on many pedals).
2. Tighten in a cross pattern, gently. PETG creeps under sustained load; the
   countersink spreads the load, but do not overtighten.
3. If the original screws are M3.5 × 8 and engage fully, items 1 or 2 replace them
   directly.
4. Keep the originals in the pedal's box so the plate can be removed without
   leaving the pedal unusable.
5. The pedal's rubber feet, if any, must be removed or the plate must pocket them;
   neither the Tumnus Deluxe nor the Mira was supplied with feet positions, so
   check before fitting.

## 5. Also for the board side

Nothing is needed. The plate latches into the slot grid with no fasteners. The
RockBoard QuickRelease Tool is only needed for OEM plates, not for these.

## 6. Open items

| Item | Action |
| --- | --- |
| Confirm M3 vs M3.5 | Micrometer the original screws, then delete the unused rows |
| Confirm original screw length | Measure; if ≥ 10 mm they may be reusable as-is |
| Confirm countersink angle | RockBoard/pedal screws are 90°; a 82° (inch) screw will sit high |
