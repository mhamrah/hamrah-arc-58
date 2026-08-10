# Hamrah Arc 58 Rev Beta hardware

Rev Beta is one fully reversible, two-layer PCB derived from the Sofle Choc
electrical and mechanical approach. Order two identical boards. The F.Cu view
is the right-hand outline; turning the board over to its B.Cu view produces the
left-hand outline. The approved 6x4 column-staggered field and four-key Arc
thumb geometry are unchanged. Its continuous rounded perimeter follows the
key field and thumb arc with practical space for routing and six M2 fasteners.

Rev Beta corrects two fabrication defects in Rev Alpha: every reverse-mount
SK6812MINI-E now has a closed 3.6 x 3.1 mm routed aperture on `Edge.Cuts`, and
J1 is rotated and moved so its mouth faces the inner split edge. Rev Alpha can
be used as a non-RGB keyboard by leaving all 28 LEDs per half unpopulated, but
per-key RGB and the corrected TRRS cable path require a new Rev Beta PCB.

The canonical KiCad project is:

```text
hardware/kicad/arc58-reversible.kicad_pro
hardware/kicad/arc58-reversible.kicad_pcb
```

There are no separate left/right PCB projects. The footprint arrangement is
reversible for the Choc hotswap sockets, SOD-123 diodes, reverse-mount
SK6812MINI-E LEDs, Helios socket, OLED header/jumpers, and TRRS jack.

## Per-half electronics

- 28 Kailh Choc v1 hotswap keys plus one clickable EC11 encoder;
- 29 1N4148W matrix diodes, with pad 1 / the printed bar as cathode;
- one continuous 28-LED SK6812MINI-E chain;
- one socketed KEEBD Helios RP2040 controller;
- one 74AHCT1G125 3.3-to-5 V RGB data buffer;
- one 0.91-inch SSD1306 128x32 I2C OLED;
- one reversible MJ-4PP-9-compatible TRRS jack; and
- reset, handedness, OLED-side jumpers, and eight labeled test pads.

The Helios/Pro-Micro pad mapping used by the PCB and QMK is:

| Function | Helios alias |
| --- | --- |
| RGB buffer input | `D3` |
| One-wire split data | `D2` |
| OLED SDA / SCL | `D1` / `D0` |
| Hand-select jumper | `D4` |
| Rows 0-4 | `C6`, `D7`, `E6`, `B4`, `B5` |
| Columns 0-5 | `F6`, `F7`, `B1`, `B3`, `B2`, `B6` |
| Encoder A / B | `F4` / `F5` |

## Assembly side selection

Use these face assignments when the finished keyboard is upright:

| Half | Face toward keycaps | Hotswap/diode/LED underside | Hand jumper | OLED jumper bank |
| --- | --- | --- | --- | --- |
| Left | B.Cu / B.SilkS | F.Cu / F.SilkS | `JP_HAND` 1-2 | front `JP1-JP4` |
| Right | F.Cu / F.SilkS | B.Cu / B.SilkS | `JP_HAND` 2-3 | back `JP5-JP8` |

Mount the Helios, OLED, encoder, and TRRS jack on the face toward the keycaps.
Mount each Choc hotswap socket, SOD-123 diode, and reverse-mount RGB LED on the
opposite/underside face. Populate the fixed F.Cu footprints (`U2`, `R1-R3`,
`C1-C2`, and `JP_HAND`) on F.Cu on both physical boards. The OLED jumper bank
is deliberately on the face opposite its OLED: front `JP1-JP4` for the left
half and back `JP5-JP8` for the right. Never bridge both OLED banks.

The RGB LED stays soldered to the underside SMD pads; its emitting face aligns
with the routed aperture beneath the switch. The package is not placed loose
on the keycap side. It is also valid to omit every RGB LED, `U2`, `R1`, and the
RGB-only capacitors if lighting is not wanted.

The TRRS pinout is identical on both halves: sleeve `GND`, ring 2 `VBUS`, tip
`SPLIT_DATA`, ring 1 unused/spare. Connect or remove TRRS only while USB is
unplugged, and do not power both halves from separate USB ports while TRRS is
installed. J1's cable mouth must face the inner split edge; the matching top
plate/case opening is 10 mm high so a normal molded plug can be fully inserted.

## Verification status

Automated checks currently prove:

- all 58 approved physical press positions and plate clearances;
- all required controller, matrix, encoder, OLED, RGB, and TRRS nets;
- one 28-LED data chain per assembled half;
- zero unrouted connections; and
- zero shorts, crossings, copper/hole/mask/silkscreen clearance violations.

KiCad reports six reviewed reversible-pad endpoint warnings and no dangling-via
warnings. The verifier pins their exact count so a change fails CI-style
verification; connectivity analysis still reports zero unrouted nets.

Run:

```sh
npm run verify
```

The board is design-checked, not hardware-proven. Order a small prototype
quantity, follow `hardware/BRING-UP-CHECKLIST.md`, and do not call the revision
production-ready until an assembled pair passes the physical and electrical
bring-up tests. The complete pair BOM is `hardware/BOM-REV-BETA.csv`.
