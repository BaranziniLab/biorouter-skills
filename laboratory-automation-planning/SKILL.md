---
name: laboratory-automation-planning
description: Plan, write, simulate and review liquid-handling robot protocols, with the Opentrons Python Protocol API for Flex and OT-2 and PyLabRobot for vendor-neutral automation (Hamilton, Tecan, Opentrons and others), from deck layout, labware, pipettes and tips to modules, serial dilutions, PCR setup and plate reads. Use for automating a bench protocol, converting a manual method to a robot, checking a protocol before a run, or planning work for a cloud lab.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/opentrons-integration, skills/pylabrobot)"
---

# Laboratory Automation Planning

A robot does exactly what the protocol says, including the mistakes. This skill turns a bench
method into a protocol that has been simulated, resource-budgeted and reviewed by a person before
anything moves. The two guides under `references/` are adapted from K-Dense Scientific Agent
Skills (MIT; see `LICENSE-UPSTREAM`).

## Safety boundary

Planning, writing and simulating are safe. **Running a physical robot is not**: it moves
liquids, sharps and sometimes hazardous material. Never start a run, home a robot or move
hardware on your own. Hand the simulated protocol to a trained operator, who checks the deck,
labware and reagents and starts the run. Biological and chemical safety rules of the lab apply
in full.

## Intake

Collect before writing code:

- The manual method, step by step, with volumes, concentrations, incubation times and mixing.
- The robot (Opentrons Flex or OT-2, Hamilton STAR, Tecan, other) and its installed modules
  (temperature, magnetic, heater-shaker, thermocycler, absorbance reader, gripper).
- Pipettes and tip types available, labware by exact definition (plate model, tube rack,
  reservoir), and the starting deck layout.
- Sample count, replicates and the plate map (from `experimental-design` when the layout is a
  statistical decision).
- Liquid properties that change handling: viscous, volatile, foaming, or cell suspensions.

## Choose the interface

| Situation | Use | Guide |
| --- | --- | --- |
| Protocol for an Opentrons Flex or OT-2 | Opentrons Python Protocol API v2 (Flex at API 2.29, OT-2 at API 2.28 per the guide), simulated with `opentrons_simulate` | `references/opentrons-integration.md` |
| One workflow that must run on several vendors' robots, or a non-Opentrons device | PyLabRobot, starting offline with the simulator backend | `references/pylabrobot.md` |
| A protocol on OpentronsAgent's tools (simulate, inspect) | OpentronsAgent, when installed, following this method | `references/opentrons-integration.md` |
| Work to be ordered from a cloud lab | Write the protocol and plate map here, simulate it, then submit through the provider's own portal or API with the person | both guides |

The Opentrons guide carries templates to start from: basic transfers, serial dilution, PCR
setup, runtime parameters and an absorbance-reader run
(`references/opentrons-integration/scripts/`). Install the pinned simulator from
`references/opentrons-integration/requirements-flex.txt` or `requirements-ot2.txt`.

## Writing the protocol

1. **Declare the deck explicitly**: every labware item with its slot and definition, every
   module and its slot, tip racks for each pipette. No implicit defaults.
2. **Choose the liquid-handling layer**: simple `transfer` and `distribute` for routine moves,
   explicit aspirate and dispense when volumes, air gaps, touch-tips or flow rates matter; Flex
   liquid classes for viscous or volatile liquids.
3. **Budget resources** before running: tips per pipette (with a margin), reagent volumes per
   well including dead volume, and run time. A run that runs out of tips at step 40 wastes the
   samples in steps 1 to 39.
4. **Parameterise** sample count and volumes as runtime parameters rather than editing code
   between runs.
5. **Label liquids** and define their starting volumes so the app and the simulation show what
   goes where.

## Validate in layers

1. Static review: the code matches the manual method step by step; volumes are within each
   pipette's range; no well is aspirated beyond what it holds.
2. Simulation: `opentrons_simulate` (or the PyLabRobot simulator) runs to completion with no
   errors or warnings, and the run log shows the expected number of transfers and tips.
3. Analysis in the Opentrons App: load the protocol, check the deck map and liquid setup.
4. Dry run on the robot with water, started by the operator.
5. First real run with a small sample set and a check of the output (volumes by weight,
   concentrations, or a plate read).

Record the protocol version, API level, robot software version and simulation log with each
run so results can be traced to the exact protocol.

## In Biorouter

- Run simulators and the PyLabRobot planning CLIs with the Developer shell; the PyLabRobot
  guide's helpers make no hardware or network connections
  (`references/pylabrobot/scripts/plan_transfers.py`,
  `references/pylabrobot/scripts/check_deck_geometry.py`).
- OpentronsAgent provides typed Opentrons tools when installed; its bundled skill defers to this
  one for method.
- GinkgoCloudLabAgent is retired; plan cloud-lab work here and submit it through the provider.
- Plate layouts, replicates and randomisation: the `experimental-design` bundle; primer and assay
  design: `primer-design`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/opentrons-integration.md` | Flex and OT-2 protocol skeletons, deck and labware, pipettes and tips, liquid classes, modules, runtime parameters, validation, failure modes, API migration |
| `references/pylabrobot.md` | Resources and decks, liquid handling, hardware backends, analytical equipment, offline simulation, operator safety gate |
