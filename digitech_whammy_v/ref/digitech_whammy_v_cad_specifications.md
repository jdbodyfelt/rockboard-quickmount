# DigiTech Whammy V Mounting Bracket — CAD Specifications & Design Parameters

This document details the outer envelope, corner hole pattern, expression sweep clearance zones, and a build123d reference script for designing custom bottom mounting plates or pedalboard brackets for the **DigiTech Whammy V** (5th Generation) pitch shifter pedal.

> **Note on Whammy IV vs. Whammy V Differences:** The Whammy V features a narrower, slightly shorter overall footprint compared to the larger Whammy IV chassis ($165.0 \text{ mm} \times 197.0 \text{ mm}$ vs $200.0 \text{ mm} \times 203.2 \text{ mm}$). Additionally, power requirements changed from 9V AC (Whammy IV) to standard 9V DC center-negative (Whammy V), though the mounting screw pattern (#6-32 UNC) remains consistent.

---

## 1. Footprint & Mounting Hole Layout

| Feature | Dimension (Metric) | Imperial Equiv. | Notes |
| :--- | :--- | :--- | :--- |
| **Total Enclosure Width (**$X$**)** | 165.0 mm | 6.500 in | Nominal outer footprint |
| **Total Enclosure Depth (**$Y$**)** | 197.0 mm | 7.756 in | Nominal outer footprint |
| **Corner Radius (**$R$**)** | 6.35 mm | 0.250 in | Outer corner fillets on stamped steel bottom plate |
| **Hole Center Distance Width (**$\Delta X$**)** | 149.0 mm | 5.866 in | Center-to-center across width |
| **Hole Center Distance Depth (**$\Delta Y$**)** | 181.0 mm | 7.126 in | Center-to-center across depth |
| **Hole Edge Offset** | 8.0 mm | 0.315 in | Center of hole from outer $X/Y$ bounding box |

---

## 2. Fastener Specifications & Clearances

* **Thread Specification:** **#6-32 UNC** machine thread (approximately 3.5 mm major diameter).
* **Screw Length:** 1/4 in (6.35 mm) or 1/2 in (12.7 mm), measured under the head.
* **Head Type:** Phillips pan-head, button-head, or round-head (non-countersunk).
* **Mount-Plate Clearance Hole Sizes:**
  * **Tight Fit:** $\varnothing$ 3.6 mm
  * **Standard Fit:** $\varnothing$ 3.7 mm
  * **3D-Printing / FDM Target:** $\varnothing$ 3.8 mm (selected for clearance over the nominal 3.5 mm major diameter; verify against the printed part).

---

## 3. Expression Pedal Sweep & Bottom Chassis Clearance

* **Treadle Overhang:** The mechanical rocker pedal extends slightly past the upper chassis frame, but the bottom plate sits on a flat, recessed steel pan.
* **Rubber Foot Placement:** The four stock rubber feet are placed near the outer corners ($15 \text{ mm}$ inset from edges). Removing them exposes the flat stamped steel base pan.
* **Raised Base Clearance:** If designing a drop-in pedalboard plate or riser, ensure a minimum **3.0 mm** material thickness to support the weight ($\approx 1.6 \text{ kg} / 3.5 \text{ lbs}$) and torque exerted during expression pedal travel.

---

## 4. Recommended Plate Thickness by Material

* **Aluminum (6061-T6 Laser/CNC):** 2.5 mm – 3.0 mm
* **Steel (Laser-cut / Powder-coated):** 1.5 mm – 2.0 mm
* **3D-Printed Plastic (PETG / ABS / ASA):** 4.0 mm – 5.0 mm base plate thickness (use 100% infill or heavy grid infill around mounting bosses).

---

## 5. build123d Reference Script

The following Python script generates a parametric mounting plate for the DigiTech Whammy V footprint using [build123d](https://build123d.readthedocs.io/).

```python
from build123d import *

# --- Parametric Dimensions (Whammy V) ---
width = 165.0       # Outer width (X)
depth = 197.0       # Outer depth (Y)
thickness = 4.0     # Base plate thickness (Z)
corner_r = 6.35     # Outer corner fillet radius

hole_dx = 149.0     # Center-to-center X distance
hole_dy = 181.0     # Center-to-center Y distance

hole_dia = 3.8      # Plain FDM clearance hole for #6-32 screw; no countersink

# --- Model Generation ---
with BuildPart() as whammy_v_bracket:
    # Outer plate sketch
    with BuildSketch() as sketch:
        Rectangle(width, depth)
        fillet(sketch.vertices(), radius=corner_r)

    extrude(amount=thickness)

    # Place 4 corner plain clearance holes
    with BuildSketch(whammy_v_bracket.faces().filter_by(Axis.Z)[-1]) as hole_sketch:
        with Locations(GridLocations(hole_dx, hole_dy, 2, 2)):
            Hole(radius=hole_dia / 2, depth=thickness)

# Export option (uncomment to write files)
# export_step(whammy_v_bracket.part, "whammy_v_bracket.step")
# export_stl(whammy_v_bracket.part, "whammy_v_bracket.stl")
```