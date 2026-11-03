# Strymon MiniSwitch Mounting Bracket — CAD Specifications & Design Parameters

This document contains the precise dimensional parameters, fastener specifications, and a build123d script reference for designing a custom mounting bracket or base plate for the **Strymon MiniSwitch** (or MultiSwitch/Favorite switch compact enclosure).

## 1. Footprint & Mounting Hole Layout

| Feature | Dimension (Metric) | Imperial Equiv. | Notes |
| ----- | ----- | ----- | ----- |
| **Total Enclosure Width (**$X$**)** | 50.8 mm | 2.000 in | Nominal outer footprint |
| **Total Enclosure Depth (**$Y$**)** | 57.1 mm | 2.250 in | Nominal outer footprint |
| **Corner Radius (**$R$**)** | 2.5 mm | 0.098 in | Outer corner fillets |
| **Hole Center Distance Width (**$\Delta X$**)** | 40.8 mm | 1.606 in | Center-to-center across width |
| **Hole Center Distance Depth (**$\Delta Y$**)** | 47.1 mm | 1.854 in | Center-to-center across depth |
| **Hole Edge Offset** | 5.0 mm | 0.197 in | Center of hole from outer $X/Y$ edges |

## 2. Fastener Specifications & Clearances

* **Thread Specification:** Metric **M3 × 0.5 mm**
* **Stock Screw Length:** 6.0 mm (flathead countersunk)
* **Clearance Hole Sizes:**
  * **Tight Fit:** $\varnothing$ 3.2 mm
  * **Standard Fit:** $\varnothing$ 3.4 mm
  * **FDM / 3D-Printing Target:** $\varnothing$ 3.5 mm (accounts for inner-diameter shrinkage)
* **Countersink Profile:**
  * **Head Angle:** 90°
  * **Head Outer Clearance Diameter:** $\varnothing$ 6.0 mm – 6.4 mm
* ⚠️ **Internal Clearance Warning:** Do **NOT** exceed **7.5 mm total screw length** (including bracket thickness) to avoid contacting internal switch wiring or the PCB chassis.

## 3. Recommended Bracket Thickness by Material

* **Aluminum (6061-T6 Laser/CNC):** 1.5 mm – 2.0 mm
* **3D-Printed Plastic (PETG / ABS / PLA):** 2.5 mm – 3.5 mm base plate thickness with 100% infill around hole bosses.

## 4. build123d Reference Script

The following Python script uses [build123d](https://build123d.readthedocs.io/) to generate a 3D model of the base plate with countersunk screw holes and export capabilities.

```python
from build123d import *

# --- Parametric Variables ---
width = 50.8        # Outer width (X)
depth = 57.1        # Outer depth (Y)
thickness = 3.0      # Base plate thickness (Z)
corner_r = 2.5       # Corner radius

hole_dx = 40.8      # Center-to-center X distance
hole_dy = 47.1      # Center-to-center Y distance

hole_dia = 3.4       # Through-hole clearance diameter
cs_dia = 6.2         # Countersink top diameter
cs_angle = 90.0      # Countersink angle in degrees

# --- Model Generation ---
with BuildPart() as miniswitch_bracket:
    # Create main plate body with filleted corners
    with BuildSketch() as sketch:
        Rectangle(width, depth)
        fillet(sketch.vertices(), radius=corner_r)
    extrude(amount=thickness)

    # Place countersunk holes at the 4 mounting positions
    with BuildSketch(miniswitch_bracket.faces().filter_by(Axis.Z)[-1]) as hole_sketch:
        with Locations(GridLocations(hole_dx, hole_dy, 2, 2)):
            CounterSinkHole(
                radius=hole_dia / 2,
                counter_sink_radius=cs_dia / 2,
                counter_sink_angle=cs_angle,
                depth=thickness
            )

# Export options (uncomment to export files)
# export_step(miniswitch_bracket.part, "strymon_miniswitch_bracket.step")
# export_stl(miniswitch_bracket.part, "strymon_miniswitch_bracket.stl")
```