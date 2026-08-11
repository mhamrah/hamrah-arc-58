# Hamrah Arc 58 Rev Beta hardware

Rev Beta is one fully reversible, two-layer PCB derived from the Sofle Choc
electrical and mechanical approach. Order two identical boards. The F.Cu view
is the right-hand outline; turning the board over to its B.Cu view produces the
left-hand outline. Rev Beta keeps the approved 6x4 column-staggered field and
updates the four-key Arc to 22 mm centers, with T1 shifted only 1 mm toward the
outer edge and T2-T4 continuing down the fan. Its continuous rounded
perimeter follows the key field and thumb arc with practical space for routing
and six M2 fasteners. The thumb-bay M2 point moves between T2 and T3 so the
fastener and its boss remain clear of the widened T4 position; use the
regenerated Rev Beta plates and case with this board.

Rev Beta corrects four fabrication defects in Rev Alpha: every reverse-mount
SK6812MINI-E now has a closed 3.6 x 3.1 mm routed aperture on `Edge.Cuts`, J1 is
rotated and moved so its mouth faces the inner split edge, and the physical
thumb-switch axes now follow the intended fan at 22 mm centers. Rev Alpha's
axes were mirrored to -10, -30, -50, and -70 degrees on the assembled left half
instead of +10, +30, +50, and +70 degrees, and its 20.5 mm thumb centers did
not meet the conservative 18 x 18 mm keycap-envelope clearance requirement. Do
not build or reorder Rev Alpha. It can only be electrically bench-tested with
all 28 LEDs per half omitted and without relying on enclosure/TRRS fit; the
intended keyboard requires a new Rev Beta PCB.

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

| Half | Face toward keycaps | Helios header holes | Hotswap/diode/LED underside | Hand jumper | OLED jumper bank |
| --- | --- | --- | --- | --- | --- |
| Left | B.Cu / B.SilkS | `L`-marked B.SilkS holes | F.Cu / F.SilkS | `JP_HAND` 1-2: D4 to 3V3 | front `JP1-JP4` |
| Right | F.Cu / F.SilkS | `R`-marked F.SilkS holes | B.Cu / B.SilkS | `JP_HAND` 2-3: D4 to GND | back `JP5-JP8` |

Mount the Helios, OLED, encoder, and TRRS jack on the face toward the keycaps.
For the Helios, solder only the two 12-hole rows marked `L` on the B.Cu/left
face or `R` on the F.Cu/right face; the offset duplicate holes belong to the
opposite assembly. Do not fill both header positions.

`JP_HAND` is a separate three-pad solder jumper on F.Cu, not a Helios header
choice. The center pad is Helios D4 (`HAND`), pad 1 is 3V3, and pad 3 is GND.
QMK reads high as left and low as right, so bridge exactly one gap: 1-2 for the
left PCB or 2-3 for the right PCB. Leaving both gaps open makes D4 float;
bridging both shorts 3V3 to GND. The original Sofle firmware normally infers
left from the USB/master half, whereas this dedicated pin lets either Arc half
be the USB master without losing its physical handedness.

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
- the physical thumb locator-hole axes on both assembled faces, independent of
  the placement transform: B.Cu/left is +10/+30/+50/+70 degrees and F.Cu/right
  is -10/-30/-50/-70 degrees;
- at least 1 mm nominal clearance between adjacent 18 x 18 mm thumb-keycap
  envelopes at the 22 mm centers;
- all required controller, matrix, encoder, OLED, RGB, and TRRS nets;
- Helios face labels and local high/low handedness-jumper instructions;
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
