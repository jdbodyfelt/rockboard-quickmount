# Preparation documentation

This folder captures what we know about the RockBoard platform and the QuickMount system **before** we design anything. It exists so that the generator's parameters are traceable to evidence instead of guesswork.

See [PLAN.md](../PLAN.md) for the staged plan that uses these documents.

## Status legend

Every number in these documents carries one of these markers:

| Marker | Meaning |
| --- | --- |
| **Official** | Published by Warwick/RockBoard or a pedal manufacturer. Source recorded. |
| **Measured** | Measured in this project with the recorded tool and date. |
| **Community** | Reported by a third party. Plausible, but must be re-measured before production use. |
| **Assumption** | Working hypothesis. Never becomes a default parameter. |
| **Open** | Not yet known. Blocks the phase that needs it. |

Rules:

1. No **Open**, **Assumption**, or **Community** value may be hard-coded as a production default. It may only appear as a parameter with a test coupon behind it.
2. Every dimension gets a source URL or a measurement record with date, tool, and operator.
3. Design to a parameter, not to a number in code. The slot interface will be defined by a small set of parameters (see [Parameters we must measure](rockboard-system.md#5-parameters-we-must-measure)) plus a tolerance profile.

## Documents

| Document | Contents |
| --- | --- |
| [rockboard-system.md](rockboard-system.md) | Board construction, model matrix, slot grid, mounting plane, and the measurements we still need. |
| [quickmount-system.md](quickmount-system.md) | How the OEM QuickMount works, the full type catalogue, the keeper lock, and the constraints for a printed equivalent. |
| [geometry-capture.md](geometry-capture.md) | Metrology procedure, tool list, record templates, tolerance budget, fit coupons, and the OEM baseline test protocol. |
| [pedal-data.md](pedal-data.md) | Pedal dimensions and screw-hole data: sources, confidence model, and the lookup pipeline. |
| [rendering-pipeline.md](rendering-pipeline.md) | Parametric CAD/STL generation: tool choice, pipeline stages, QA gates, print orientation, material profiles. |
| [input-schema.md](input-schema.md) | YAML/JSON schema for pedals, boards, printer profiles, and batch manifests. |
| [sources.md](sources.md) | Consolidated source list. |

## Top open questions

These are ordered by how much they block the plan:

1. **Slot opening width, slot length, and pitch.** Without these there is no printable interface. (Open)
2. **Keeper kinematics.** How the plate locks, what the release direction is, and what force it resists. (Open — hypotheses in [quickmount-system.md](quickmount-system.md#4-hypotheses-to-test))
3. **Mounting plane angle and standoff.** The catalogue advertises a "10° angled surface"; we need to know whether the top sheet is inclined and how much clear height exists under it. (Open)
4. **Screw sizes used by pedal makers.** Thread, length, and depth vary by brand. (Open, but bounded by the OEM type library — see [pedal-data.md](pedal-data.md#3-the-oem-type-library-shortcut))
5. **Whether a printed keeper can meet the OEM retention and cycle life** with commodity filament. (Open — Phase 1 gate)

## Related documents

- Slot geometry parameter table: [rockboard-system.md](rockboard-system.md#5-parameters-we-must-measure)
- Tolerance and coupon design: [geometry-capture.md](geometry-capture.md#5-tolerance-budget)
- Definition of done: [PLAN.md](../PLAN.md#1-objective-and-definition-of-done)

## Licensing note

The repository is GPL-3.0. Do not copy proprietary drawings, CAD files, or unlicensed databases into this repository. Public vendor pages may be cited and summarised; redistributable measurements must be our own.
