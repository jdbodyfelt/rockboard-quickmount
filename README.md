# rockboard-quickmount

Reverse engineering of Warwick's RockBoard QuickMount for custom pedal designs.

The goal is to extend the QuickMount system to pedals it does not cover: from a pedal name or a small YAML description to a printable, slot-compatible mounting plate.

## Status

Preparation and planning. No generator code yet — the interface dimensions must be measured first.

- [PLAN.md](.agents/PLAN.md) — staged plan from user input to finished STLs, with gates, risks, and decisions.
- [docs/](docs/README.md) — preparation documentation: board geometry, QuickMount mechanics, metrology, pedal data, and the rendering pipeline.
- [TODO.md](.agents/TODO.md) — original project brief.

## Approach in one paragraph

Measure a real board and a real QuickMount plate, parameterise the slot/keeper interface, prove it with printed fit coupons, then generate plates from pedal data. Where RockBoard already publishes a QuickMount type for a pedal, reuse that type's verified screw pattern instead of measuring the pedal. Every dimension carries a source and confidence level, and the generator refuses to run on unverified data.

Manufacturing target: **Kea Modelling** (FDM, Mt Eden, Auckland) in **PETG** — see [docs/manufacturing.md](docs/manufacturing.md).

## Generating plates

```bash
pip install build123d trimesh shapely rtree pyyaml matplotlib
python -m quickmount.build --step      # keeper ring + arrangements into out/
python -m quickmount.validate          # geometry checks against the board profile
```

Outputs: `keeper_ring`, `keeper_arrangement_2ring` (matches the reference clip),
`keeper_arrangement_3ring`.

Keeper geometry in [catalog/clips/](catalog/clips), board geometry in
[catalog/boards/](catalog/boards), housing families in [catalog/housings/](catalog/housings). The slot dimensions there are **provisional**
until measured with callipers — see
[docs/quickmount-mechanism.md](docs/quickmount-mechanism.md#6-provisional-board-dimensions).
Screws: [docs/screws.md](docs/screws.md).

Scope is currently the **mechanism only**: the C-shaped keeper ring and bar
arrangements of it, reproduced from a measured RockBoard-compatible clip. Pedal
baseplates are deferred until the ring is proven on a real board. Mechanism,
measurements and the open question: [docs/quickmount-mechanism.md](docs/quickmount-mechanism.md).

## Licence

GPL-3.0 — see [LICENSE](LICENSE).
