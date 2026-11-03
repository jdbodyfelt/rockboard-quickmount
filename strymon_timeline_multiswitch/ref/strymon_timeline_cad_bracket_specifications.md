# Strymon TimeLine Mounting Bracket — CAD Specifications & Design Parameters

This document contains the precise dimensional parameters, fastener tolerances, and a build123d script reference for designing a custom mounting bracket or base plate for the **Strymon TimeLine** delay pedal.

## 1. Footprint & Mounting Hole Layout

| Feature | Dimension (Metric) | Imperial Equiv. | Notes | 
| ----- | ----- | ----- | ----- | 
| **Total Enclosure Width (**$X$**)** | 171.0 mm | 6.732 in | Nominal outer footprint | 
| **Total Enclosure Depth (**$Y$**)** | 130.0 mm | 5.118 in | Nominal outer footprint | 
| **Corner Radius (**$R$**)** | 3.0 mm | 0.118 in | Outer corner fillets | 
| **Hole Center Distance Width (**$\Delta X$**)** | 158.0 mm | 6.220 in | Center-to-center across width | 
| **Hole Center Distance Depth (**$\Delta Y$**)** | 117.0 mm | 4.606 in | Center-to-center across depth | 
| **Hole Edge Offset** | 6.5 mm | 0.256 in | Center of hole from outer $X/Y$ edges | 

## 2. Fastener Specifications & Clearances

* **Thread Specification:** Metric **M3 × 0.5 mm**

* **Stock Screw Length:** 6.0 mm (flathead countersunk)

* **Clearance Hole Sizes:**

  * **Tight Fit:** $\varnothing$ 3.2 mm

  * **Standard Fit:** $\varnothing$ 3.4 mm

  * **FDM / 3D-Printing Target:** $\varnothing$ 3.5 mm (accounts for inner-diameter shrink)

* **Countersink Profile:**

  * **Head Angle:** 90°

  * **Head Outer Clearance Diameter:** $\varnothing$ 6.0 mm – 6.4 mm

* ⚠️ **Internal Clearance Warning:** Do **NOT** exceed **8 mm total screw length** (including bracket thickness). Screws penetrating further than 4 mm past the chassis wall risk damaging internal double-sided PCB components.

## 3. Plate Clearances & Material Recommendations

### Relief Zones

* **Serial Label Recess:** Allocate a cutout or recessed pocket (min. 0.8 mm depth) in the center-top area to prevent scraping or tearing the serial number sticker.

* **Perimeter Margin:** Maintain a 5.0 mm outer perimeter clear of obstructions to flush-mount against the enclosure flange.

### Recommended Thickness by Material

* **Aluminum (6061-T6 Laser/CNC):** 1.5 mm – 2.0 mm

* **Stainless Steel:** 1.2 mm – 1.5 mm

* **3D-Printed Plastic (PETG / ABS / PLA):** 3.0 mm – 4.0 mm base plate thickness (use 100% infill around screw mounting bosses).

## 4. build123d Reference Script

The following Python script uses [build123d](https://build123d.readthedocs.io/) to generate a parametric 3D model of the base plate with countersunk holes.

```python
from build123d import *

# --- Parametric Variables ---
width = 171.0       # Outer width (X)
depth = 130.0       # Outer depth (Y)
thickness = 3.0     # Base plate thickness (Z)
corner_r = 3.0      # Corner radius

hole_dx = 158.0     # Center-to-center X distance
hole_dy = 117.0     # Center-to-center Y distance

hole_dia = 3.4      # Through-hole clearance diameter
cs_dia = 6.2        # Countersink top diameter
cs_angle = 90.0     # Countersink angle in degrees

# --- Model Generation ---
with BuildPart() as bracket:
    # Create main plate body with filleted corners
    with BuildSketch() as sketch:
        Rectangle(width, depth)
        fillet(sketch.vertices(), radius=corner_r)
    extrude(amount=thickness)

    # Place countersunk holes at the 4 mounting positions
    with BuildSketch(bracket.faces().filter_by(Axis.Z)[-1]) as hole_sketch:
        with Locations(GridLocations(hole_dx, hole_dy, 2, 2)):
            CounterSinkHole(
                radius=hole_dia / 2,
                counter_sink_radius=cs_dia / 2,
                counter_sink_angle=cs_angle,
                depth=thickness
            )

# Export to STEP or STL format (optional)
# export_step(bracket.part, "strymon_timeline_bracket.step")
# export_stl(bracket.part, "strymon_timeline_bracket.stl")
```