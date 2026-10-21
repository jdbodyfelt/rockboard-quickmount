# Sources

All sources retrieved 2026-10-21 unless noted. Keep this list current: every document in `/docs` should cite one of these or add a new entry.

## Primary vendor sources

| Source | URL | Used for | Notes |
| --- | --- | --- | --- |
| RockBoard catalogue (PDF, 49 pages) | <https://www.rockboard.de/downloads/RockBoard_Catalog.pdf> | Construction, model matrix, QuickMount type catalogue, MOD-slot exclusion for Duo, UH/UV dimensions | Text extracted; drawings are images and were not used for dimensions |
| RockBoard home | <https://www.rockboard.de/en/> | Product positioning, 16-board range | |
| RockBoard pedalboards overview | <https://www.rockboard.de/en/pedalboards/> | Model families | |
| RockBoard Duo 2.0 | <https://www.rockboard.de/en/pedalboards/duo-20/> | Height including rubber feet (35–58 mm) | |
| QuickMount overview | <https://www.rockboard.de/en/quickmounts/> | How the system attaches and releases; no permanent modification | |
| QuickMount Finder | <https://www.rockboard.de/en/quickMountFinder/> | Pedal-to-type compatibility tool | JavaScript application; automation not attempted |
| PedalPedia | <https://www.rockboard.de/en/pedalPedia/> | Vendor pedal catalogue | JavaScript application; backing API at `api.rockboard.de` only exposed client-environment endpoints in a limited probe. Terms not yet reviewed |

## Community and third-party sources

| Source | URL | Used for | Licence / caveat |
| --- | --- | --- | --- |
| Pedal-Research | <https://github.com/emilwu/Pedal-Research> | Example of per-pedal YAML with physical dimensions and source annotations | **No declared licence.** Reference and lead generation only; do not copy data |

## Tooling

| Source | URL | Used for |
| --- | --- | --- |
| build123d | <https://github.com/gumyr/build123d> | Proposed B-rep CAD kernel (Apache-2.0) |
| CadQuery | <https://github.com/CadQuery/cadquery> | Alternative B-rep kernel |
| OpenSCAD | <https://openscad.org/> | Fallback CSG modeller (GPL-2.0) |
| trimesh | <https://github.com/mikedh/trimesh> | Mesh validation |
| manifold | <https://github.com/elalish/manifold> | Robust mesh booleans (Apache-2.0) |

## Sources deliberately not used

- Search-engine result pages: automated fetches were blocked or returned unusable content during preparation. Do not depend on scraping a search engine in the pipeline; use site search, sitemaps, and documented APIs where permitted.
- Retailer pages: useful for dimension corroboration, but not yet captured. Add them per pedal with a retrieval date.
- Forum posts and videos: acceptable as leads only, never as sole evidence for a production dimension.

## Vendor claims that still need verification

| Claim | Source | Why it matters |
| --- | --- | --- |
| "10° angled surface" | Catalogue p.3 | Affects pedal stance and riser design; the exact geometry is unconfirmed |
| "Slotted design for easy pedal mounting" | Catalogue p.3 | Confirms the mounting interface but gives no dimensions |
| QuickMount plates "snap securely and firmly" | QuickMount page | Marketing claim; retention must be measured |
| Duo 2.0–2.3 excluded from MOD-slot drawer | Catalogue p.8 | Implies no usable MOD slots on Duo; confirm physically |
