# Line 6 Modeler Series (DL4 / FM4 / MM4 / DM4) Mounting Bracket — CAD Specifications & Design Parameters

This document details the outer envelope, hole placement, battery door clearances, and a build123d reference script for designing custom bottom mounting plates or pedalboard brackets for classic Line 6 4-switch modeler pedals (**DL4 MkI**, **FM4**, **MM4**, **DM4**, **AM4**).

## 1. Footprint & Mounting Hole Layout

| Feature | Dimension (Metric) | Imperial Equiv. | Notes |
| ----- | ----- | ----- | ----- |
| **Total Enclosure Width (**$X$**)** | 254.0 mm | 10.000 in | Nominal outer footprint |
| **Total Enclosure Depth (**$Y$**)** | 152.0 mm | 6.000 in | Nominal outer footprint |
| **Corner Radius (**$R$**)** | 9.5 mm | 0.375 in | Fillet radius on outer cast aluminum chassis |
| **Hole Center Distance Width (**$\Delta X$**)** | 238.0 mm | 9.370 in | Center-to-center across width |
| **Hole Center Distance Depth (**$\Delta Y$**)** | 136.0 mm | 5.354 in | Center-to-center across depth |
| **Hole Edge Offset** | 8.0 mm | 0.315 in | Center of hole from outer $X/Y$ bounding box |

## 2. Fastener Specifications & Clearances

* **Thread Specification:** Metric **M3 × 0.5 mm**
* **Stock Screw Length:** 6.0 mm (flathead countersunk)
* **Clearance Hole Sizes:**
  * **Tight Fit:** $\varnothing$ 3.2 mm
  * **Standard Fit:** $\varnothing$ 3.4 mm
  * **3D-Printing / FDM Target:** $\varnothing$ 3.5 mm (accounts for inner-diameter shrink)
* **Countersink Profile:**
  * **Head Angle:** 90°
  * **Head Outer Diameter:** $\varnothing$ 6.0 mm – 6.4 mm

## 3. Battery Door Cutout & Clearance Relief

The classic Line 6 chassis contains a bottom-accessible 4× C-cell battery compartment door.

* **Battery Door Cutout Dimensions:** **164.0 mm (W) × 62.0 mm (D)**
* **Door Location:** Centered horizontally ($X$) and slightly offset toward the front edge.
* **Latch Clearance:** If designing a solid full-coverage plate without a central cutout, provide a minimum **4.0 mm pocket relief** to clear the battery door tabs and slider clip.

## 4. Recommended Plate Thickness by Material

* **Aluminum (6061-T6 Laser/CNC):** 2.0 mm – 3.0 mm
* **3D-Printed Plastic (PETG / ABS / PLA):** 3.5 mm – 5.0 mm (recommend 100% infill around screw mounting bosses)

---

## 5. build123d Reference Script

The following Python script generates a parametric mounting plate for the Line 6 modeler footprint using [build123d](https://build123d.readthedocs.io/).

```python
from build123d import *

# --- Parametric Dimensions ---
width = 254.0       # Outer width (X)
depth = 152.0       # Outer depth (Y)
thickness = 3.0     # Base plate thickness (Z)
corner_r = 9.5      # Outer corner fillet radius

hole_dx = 238.0     # Center-to-center X distance
hole_dy = 136.0     # Center-to-center Y distance

hole_dia = 3.5      # Through-hole clearance diameter
cs_dia = 6.2        # Countersink top diameter
cs_angle = 90.0     # Countersink angle in degrees

# Battery door relief cutout dimensions
bat_w = 164.0
bat_d = 62.0

# --- Model Generation ---
with BuildPart() as line6_bracket:
    # Outer plate sketch with battery cutout
    with BuildSketch() as sketch:
        Rectangle(width, depth)
        fillet(sketch.vertices(), radius=corner_r)
        # Cut out center for battery compartment clearance
        Rectangle(bat_w, bat_d, mode=Mode.SUBTRACT)

    extrude(amount=thickness)

    # Place 4 corner countersunk holes
    with BuildSketch(line6_bracket.faces().filter_by(Axis.Z)[-1]) as hole_sketch:
        with Locations(GridLocations(hole_dx, hole_dy, 2, 2)):
            CounterSinkHole(
                radius=hole_dia / 2,
                counter_sink_radius=cs_dia / 2,
                counter_sink_angle=cs_angle,
                depth=thickness
            )

# Export option (uncomment to write files)
# export_step(line6_bracket.part, "line6_modeler_bracket.step")
# export_stl(line6_bracket.part, "line6_modeler_bracket.stl")
```