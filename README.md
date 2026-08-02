# Hamrah Arc 58

A low-profile, split 58-input keyboard built around Kailh Choc v1 hotswap
switches, KEEBD Helios RP2040 controllers, per-key RGB, OLEDs, clickable
encoders, and a fully reversible PCB. The design keeps the approved Sofle Choc
6x4 column-staggered field and replaces the original bottom cluster with a
four-key inward/downward Arc thumb fan.

Each half has 29 press inputs:

- 24 column-staggered main keys;
- four Arc thumb keys; and
- one clickable rotary encoder.

![Hamrah Arc 58 layout](output/keyboard-layout.svg)

## Geometry

All dimensions live in `layout.config.json`.

| Parameter | Value |
| --- | ---: |
| Main matrix pitch | 19.05 x 19.05 mm |
| Choc plate cutout | 14 x 14 mm |
| Choc keys per half | 28 |
| Clickable encoders per half | 1 |
| Thumb center spacing | 20.5 mm |
| Thumb key rotations | 10, 30, 50, 70 degrees |
| Mounting holes per half | 6 x 2.2 mm |

## Generate and verify

Node.js 18 or newer and KiCad 9 are required.

```sh
npm run generate
npm run verify
```

Generation creates the mirrored layout, a US Letter 1:1 paper test, exact key
positions, and left/right top and bottom plate SVG/DXF files under `output/`.
Print the paper test at Actual Size / 100% and confirm its calibration bar is
exactly 50 mm before ordering plates.

The single native PCB project is:

```text
hardware/kicad/arc58-reversible.kicad_pro
hardware/kicad/arc58-reversible.kicad_pcb
```

Order two copies of the same Rev B PCB. In the assembled keyboard, the B.Cu
face points toward the keycaps on the left half and the F.Cu face points toward
the keycaps on the right half. Detailed component-side selection, verified pin
mapping, DRC status, and safety notes are in `hardware/README.md`; the pair BOM is
`hardware/BOM-REV-B.csv`.

## Prototype status

The routed board passes the repository's structural and electrical checks:
zero unrouted connections and zero shorts, crossings, or fabrication-clearance
violations. QMK is configured for Helios, a one-wire TRRS split, OLED, encoder,
and a 28+28 RGB Matrix. The default firmware also compiles successfully against
current upstream QMK; the ignored local UF2 is generated at
`output/firmware/arc58-rev-b-default.uf2`.

This is still a prototype until a fabricated pair passes
`hardware/BRING-UP-CHECKLIST.md`. Choc switches plug into soldered hotswap
sockets; the switches themselves are not soldered to the PCB. Use a small
prototype order and verify switch/plate fit, diode and LED orientation, USB
current, every key, both encoders, both OLEDs, RGB, and the split link before a
larger run.
