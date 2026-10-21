# Manufacturing — Kea Modelling

Selected manufacturer: **Kea Modelling**, Mt Eden, Auckland, New Zealand — <https://keamodelling.com/>.

This document records what the vendor can and cannot do, the resulting material decision, design rules for their process, and what we must calibrate before trusting a printed part.

All vendor facts below are **Official** (vendor website), retrieved 2026-10-21.

## 1. Vendor capability

| Item | Value |
| --- | --- |
| Process | FDM (fused deposition modelling), large-format |
| Build volume | 330 × 320 × 325 mm (W × D × H) |
| Materials | **PLA and PETG only** |
| Colours | Wide range for both materials; non-stock colours add ~1 day |
| Instant-order limit | Up to 500 g per part; 10 STL files per order, 100 MB each |
| Larger/heavier parts | Split into sections after a free consultation |
| Input format | STL (binary or ASCII; must be printable/manifold) |
| Pricing | Material weight + machine time; most prints NZ$5–NZ$60 |
| Turnaround | Printed and dispatched in 3–4 days |
| Delivery | Free pickup (Mt Eden) or NZ-wide courier (site lists NZ$12) |
| Payment | Stripe |
| Design service | Free 30-minute consultation; fixed quote at NZ$50/hr; 2 revisions; first print free (≤ 500 g) |
| File ownership | Customer retains ownership of uploaded models and commissioned designs; vendor will not reuse without permission |
| Marketing | Placing an order grants a non-exclusive licence to use images of the work for marketing (check the exact clause; request an opt-out if needed) |
| Faults | Reprint or refund for print failures, wrong material, or wrong colour (Consumer Guarantees Act 1993) |
| Constraints | Non-manifold or unprintable files may be rejected before printing |

Not published and therefore **Open**:

- layer height and nozzle diameter used for instant orders
- default wall count, infill pattern, and infill density
- achievable dimensional tolerance (XY and Z)
- hole shrinkage and minimum hole diameter
- minimum wall thickness and minimum feature size
- maximum unsupported overhang and bridge length
- whether the customer can specify print orientation
- surface finish and support-removal marks
- whether STEP or 3MF files are accepted

These are not blockers to design, but they are blockers to releasing a validated profile. Phase 1 must calibrate them with a vendor-printed coupon.

## 2. Material decision

**Use PETG for every functional part.** This is now a decided parameter, not an open choice.

| Material | Verdict | Reason |
| --- | --- | --- |
| PLA | Rejected for functional plates | Vendor states it warps/softens above ~60 °C, is brittle, and is not suitable for hot cars or sustained load. A pedalboard lives in vehicles and on stages. |
| PETG | **Selected** | Impact resistant, UV/outdoor stable, vendor claims heat tolerance to ~80 °C, and "slightly flexible (snap-fit friendly)" — the best available match for a keeper/snap feature. |

Consequences:

1. The keeper and any compliant feature must be designed for PETG's creep behaviour under sustained preload.
2. The vendor's "~80 °C" figure is a material claim, not a design allowable under load. Heat-deflection under load is lower. Test at **50 °C and 70 °C**, because a closed vehicle in summer can exceed 70 °C.
3. ASA and PA-CF are **not available** through Kea. They remain possible in-house or via a second vendor, but they are no longer on the critical path and must not appear as supported profiles in v0.1.
4. PLA may be used only for fit-check prototypes that never see service; the generator should mark such outputs `prototype: true`.

## 3. Design rules for FDM in PETG

Starting rules for the generator's default profile. They are hypotheses until the vendor coupon confirms them.

| Feature | Rule | Rationale |
| --- | --- | --- |
| Minimum wall | 1.2 mm absolute; 1.6–2.0 mm preferred | At least three 0.4 mm perimeters |
| Screw bosses | Outer diameter ≥ 2.2 × screw diameter; wall ≥ 1.6 mm | Prevents splitting under screw load |
| Clearance holes | M3 → 3.4 mm; M4 → 4.5 mm as a start; verify with the coupon | FDM holes print undersize |
| Snap-fit strain | ≤ 1.5 % for repeated use (PETG yields around 4–5 %) | Limits creep and cracking |
| Compliant beam thickness | ≥ 0.8 mm; length ≥ 5 × thickness | Printable and durable |
| Internal fillets | ≥ 0.5 mm at load paths | Reduces stress concentration |
| Lead-in chamfers | ≥ 0.5 mm on tabs and slot entries | Prevents elephant-foot interference |
| Flat underside | Required on the board-contact face | No supports on a mating surface |
| Bridges | ≤ 8–10 mm where possible; orient to avoid | PETG sags |
| Overhang | ≤ 45° where possible; report anything steeper | Support marks hurt fit |
| Counterbores | Preferred over countersinks for screw heads | Cleaner and more dimensionally stable |
| Minimum feature | 0.8 mm positive feature | Below this, FDM is unreliable |
| Warping | Rib large flat plates; keep thickness uniform | PETG warps on large flats |
| Print orientation | Load along extrusion direction; specify in the order note | FDM is anisotropic |

The slot/tab clearances from [geometry-capture.md](geometry-capture.md#5-tolerance-budget) remain the governing values; these rules constrain how the part is built around them.

## 4. Process calibration (vendor coupon)

Before the first production plate, order a **calibration coupon** from Kea through the instant-quote flow. One coupon set contains:

1. A 30 mm cube for X/Y/Z shrinkage.
2. A hole ladder: 3.0, 3.2, 3.4, 3.6, 4.0, 4.5, 5.0 mm, each 6 mm deep.
3. A wall ladder: 0.8, 1.0, 1.2, 1.6, 2.0 mm.
4. A snap-beam ladder at 1.0 %, 1.5 %, 2.0 % strain.
5. Five slot tabs at the clearance variants from the fit-coupon ladder.
6. Embossed labels and a 20 mm scale bar.

Order **two copies in separate orders** to measure repeatability. Measure with calipers, record mean and spread, and store the result as the vendor printer profile:

```yaml
id: kea_petg_instant
vendor: kea_modelling
material: PETG
validated: false        # flip to true only after measurement
calibration_date: null
x_error_mm: null
y_error_mm: null
z_error_mm: null
hole_shrink_mm: null
layer_height_mm: null
```

Until `validated: true`, the CLI must warn on every generated part.

## 5. Ordering workflow

1. Generate the part with `--printer kea_petg_instant`; the exporter emits binary STL in millimetres, a single manifold solid.
2. Check the order limits: each part ≤ 500 g (all expected plates are far below), at most 10 STLs per order.
3. Name files deterministically so the vendor's queue and our manifest agree: `{pedal_id}__{board}__petg__r{hash}.stl`.
4. Include an order note stating material (PETG), colour, and the required print orientation.
5. Batch related plates into one order to pay one shipping fee; split batches over 10 files into multiple orders.
6. Record the quote and order ID in `docs/measurements/kea-orders.csv` (date, items, mass, price, lead time).
7. On receipt, photograph and measure each part before assembly; log the measurements against the design.

Everything the vendor needs must survive the upload: if the STL is non-manifold or self-intersecting, they may reject it. Our validation gates already require a single watertight solid, which matches their acceptance criterion.

## 6. Cost and lead time

- Expect plates in the NZ$5–NZ$20 range each at typical sizes; confirm with a real quote rather than extrapolating.
- Shipping is per order, so batch by rig rather than by pedal.
- Plan 3–4 days dispatch plus courier time for each design iteration. Phase 1's A/B experiments should be batched into as few orders as possible.
- The free 30-minute consultation and first-print-free offer can absorb one prototype round; use them deliberately.

## 7. Questions for the free consultation

1. What layer height and nozzle diameter do instant orders use?
2. What wall count, infill pattern, and density are defaults, and can I change them?
3. Can I specify print orientation, and how is it communicated?
4. What XY/Z dimensional tolerance do you achieve, and do you have measured data for holes?
5. What are your minimum wall and feature sizes for PETG?
6. How do you handle supports on mating faces, and what marks do they leave?
7. Will you print my calibration coupon and report measured dimensions?
8. Which PETG brand do you use, and does colour affect mechanical properties?
9. Do you offer annealing or vapour smoothing? (Assumed no.)
10. Can you keep a validated print profile on file for repeat orders?
11. Can you accept STEP or 3MF, or only STL?
12. What lead time applies to a 10–20 plate batch?
13. Can my parts be excluded from marketing images? (The terms grant an image licence by default.)

## 8. Risk notes specific to this vendor

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Only PLA/PETG available | No engineering-grade polymer for the keeper | Design for PETG; test creep at 50/70 °C; keep an in-house ASA/PA-CF path as a fallback |
| Vendor tolerance and DFM unknown | First parts may not fit | Coupon order before production; validate profile |
| Single vendor, single region | Lead time and capacity risk | Keep the output format standard (STL + manifest) so any FDM vendor can print it |
| Instant-order limits (500 g, 10 files) | Batch friction | Batch splitter; expect plates well under 500 g |
| Orientation may be vendor-chosen | Anisotropic strength may vary | Ask; encode orientation in the order note; test parts from two orientations |
| Marketing image licence | Privacy or IP concern | Request opt-out if designs are confidential |
| 3–4 day dispatch per iteration | Slow validation loops | Batch experiments; print multiple variants per order |

## 9. Sources

- 3D printing service: <https://keamodelling.com/3d-printing>
- Materials guide: <https://keamodelling.com/materials>
- CAD design service: <https://keamodelling.com/cad-design>
- Terms of service: <https://keamodelling.com/terms>
- Returns and shipping: <https://keamodelling.com/returns>
