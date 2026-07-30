# Hamrah Arc 58

An editable physical layout study for a low-profile split keyboard using Kailh Choc v1 (PG1350) switches, the official Sofle Choc matrix spacing, mirrored clickable Alps encoders, and a custom four-key thumb arc. The name counts 58 press inputs: 56 Choc switches plus two encoder clicks.

The design keeps 29 press inputs on each half:

- a 6 × 4 column-staggered field;
- one mirrored, clickable Alps EC11E15244G1 rotary encoder; and
- four thumb keys.

The changed thumb cluster begins exactly halfway between the two innermost ortholinear columns. Each following key moves inward and sharply down in a Draculad-inspired fan, with progressively stronger rotation to follow the thumb's natural sweep.

![Hamrah Arc 58 layout](output/keyboard-layout.svg)

## Current geometry

All dimensions are millimetres and live in [`layout.config.json`](layout.config.json).

| Parameter | Value |
| --- | ---: |
| Sofle Choc matrix pitch | 19.05 × 19.05 |
| Plate cutout | 14 × 14 |
| Choc switches per half | 28 |
| Clickable encoders per half | 1 × Alps EC11E15244G1 |
| Encoder plate opening | 7.2 diameter |
| Thumb center spacing | 20.5 |
| T1 drop below lower matrix key | 19 |
| Thumb segment angles | 16°, 36°, 56° |
| Thumb key rotations | 10°, 30°, 50°, 70° |

The matrix copies the official Sofle Choc center spacing, mirrored into left-half outer-to-inner order. Its six column offsets are 7.4, 7.4, 2.5, 0, 2.5, and 5 mm, making the middle-finger column the highest. Thumb key T1 is anchored between columns C5 and C6; T2–T4 use the Draculad's approximately 20-degree progression as a reference and arc decisively inward and down. The 19 mm drop leaves about 3.61 mm between the T1 and C5R4 keycap outlines and 2.47 mm between T1 and C6R4.

## Generate and verify

Node.js 18 or newer is the only requirement.

```sh
npm run generate
npm test
```

Generation writes:

- `output/keyboard-layout.svg` — mirrored visual layout;
- `output/left-half-paper-test-letter.svg` — US Letter paper fit test with a 50 mm calibration bar;
- `output/pdf/left-half-paper-test-letter.pdf` — ready-to-print PDF copy of the fit test;
- `output/key-positions.json` — exact switch centers and rotations;
- `output/left-half-plate.svg` — one-to-one left plate geometry; and
- `output/left-half-plate.dxf` — millimetre DXF with separate outline and cutout layers.

## Prototype before fabrication

This draft defines key geometry and a simple convex prototype plate. It is not yet a routed PCB or production case. Print `output/left-half-paper-test-letter.svg` at Actual Size / 100%, disable any Fit to Page option, and confirm its calibration bar measures exactly 50 mm. The PCB must use PG1350-compatible Choc v1 footprints or sockets, and the keycaps must use the proprietary Choc v1 two-post mount. Each half uses the Sofle Choc's modified vertical EC11E footprint, populated with a clickable Alps Alpine EC11E15244G1: a 12 × 11.6 mm body, 6 mm diameter × 20 mm shaft, 30 detents, 15 pulses, and 0.5 mm push travel. The fit model reserves an 18 mm knob envelope and a 7.2 mm panel opening.

After the thumb arc is comfortable, the component coordinates can be used to place switch and encoder footprints in KiCad and to shape the final plate and case around the controller, connector, fasteners, knobs, and hotswap sockets. Each encoder click can occupy the former inner-key matrix position; encoder rotation additionally needs two MCU inputs per half.
