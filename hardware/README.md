# Hamrah Arc 58 Rev Gamma hardware

Rev Gamma is one fully reversible, two-layer PCB derived from the Sofle Choc
electrical and mechanical approach. Order two identical boards. The F.Cu view
is the right-hand outline; turning the board over to its B.Cu view produces the
left-hand outline. Rev Gamma keeps the approved 6x4 column-staggered field and
updates the four-key Arc to 21.25 mm centers, with T1 shifted only 1 mm toward
the outer edge and T2-T4 continuing down the fan. T3 rotates to 45 degrees and
T4 rotates to 55 degrees; the final 45-degree center step moves T4 3.14 mm
outward and 2.59 mm upward from its former position, increasing T3-T4 keycap
clearance while following the paper-fit thumb sweep. Its continuous rounded
perimeter follows the key field and thumb arc with practical space for routing
and six M2 fasteners. The thumb-bay M2 point moves between T2 and T3 so the
fastener and its boss remain clear of the widened T4 position; use the
regenerated Rev Gamma plates and case with this board.

Each EC11 encoder is centered in the empty bay between the nearest 16.5 mm C6
keycap edge and the curved inner PCB edge. With the specified 18 mm knob, this
leaves 9.17 mm nominal clearance on both sides. H4 moves farther down the inner
edge so its CNC boss retains 3.5 mm clearance from the knob envelope and 3.1
mm from the case outline.

Rev Gamma retains the five fabrication corrections introduced in Rev Beta:
every reverse-mount
SK6812MINI-E now has a closed 3.6 x 3.1 mm routed aperture on `Edge.Cuts`, J1 is
rotated and moved so its mouth faces the inner split edge, and the physical
thumb-switch axes now follow the intended fan at 21.25 mm centers. The encoder
also uses equal knob clearance to C6 and the inner edge. Rev Alpha's physical
axes mirrored the then-approved 10/30/50/70-degree fan on the assembled left
half, and its 20.5 mm thumb centers did not meet the conservative 18 x 18 mm
keycap-envelope clearance requirement. Rev Gamma uses the refined
10/30/45/55-degree physical fan.

Rev Gamma also corrects the thumb-diode assembly problem found while building
Rev Beta. D29 was too close to the inner Choc hotswap socket, while D26-D28
drifted progressively farther from their switches. Gamma places D26-D29 from
reviewed switch-local offsets, gives D27 and D29 extra clearance for the
reversible COL4 route, flips D29's pad order along the same tangent, and uses
local vias instead of a jumper. No switch, mounting-hole, plate, or enclosure
geometry changed from Beta. A Beta board may be bench-tested with careful
diode rework, but it should not be reordered.

Do not build or reorder Rev Alpha. It can only be electrically bench-tested
with all 28 LEDs per half omitted and without relying on enclosure/TRRS fit;
the intended keyboard requires a Rev Gamma PCB.

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
- reset, automatic header-position handedness, OLED-side jumpers, and seven
  labeled test pads.

The Helios/Pro-Micro pad mapping used by the PCB and QMK is:

| Function | Helios alias |
| --- | --- |
| RGB buffer input | `D3` |
| One-wire split data | `D2` |
| OLED SDA / SCL | `D1` / `D0` |
| Automatic hand detect | `D4` (high = left, low = right) |
| Rows 0-4 | `C6`, `D7`, `E6`, `B4`, `B5` |
| Columns 0-5 | `F6`, `F7`, `B1`, `B3`, `B2`, `B6` |
| Encoder A / B | `F4` / `F5` |

## Assembly side selection

Use these face assignments when the finished keyboard is upright:

| Half | Face toward keycaps | Helios header holes | Hotswap/diode/LED underside | Hand detection | OLED jumper bank |
| --- | --- | --- | --- | --- | --- |
| Left | B.Cu / B.SilkS | `L`-marked B.SilkS holes | F.Cu / F.SilkS | automatic: D4 pulled to 3V3 | front `JP1-JP4` |
| Right | F.Cu / F.SilkS | `R`-marked F.SilkS holes | B.Cu / B.SilkS | automatic: D4 pulled to GND | back `JP5-JP8` |

Mount the Helios, OLED, encoder, and TRRS jack on the face toward the keycaps.
For the Helios, solder only the two 12-hole rows marked `L` on the B.Cu/left
face or `R` on the F.Cu/right face; the offset duplicate holes belong to the
opposite assembly. Do not fill both header positions.

The two physical D4 header holes are intentionally isolated. The `L`-position
D4 hole is `HAND_L` and R4 pulls it to 3V3; the `R`-position D4 hole is
`HAND_R` and R5 pulls it to GND. Populate both 10 kohm resistors on every PCB.
The installed Helios only contacts the D4 hole belonging to its selected
header position, so QMK reads high on the physical left half and low on the
physical right half. There is no hand-select jumper, both controllers use the
same UF2, and either half can be the USB master. Do not electrically join the
two alternative D4 holes.

Mount each Choc hotswap socket, SOD-123 diode, and reverse-mount RGB LED on the
opposite/underside face. Populate the fixed F.Cu footprints (`U2`, `R1-R5`,
and `C1-C2`) on F.Cu on both physical boards. The OLED jumper bank
is deliberately on the face opposite its OLED: front `JP1-JP4` for the left
half and back `JP5-JP8` for the right. Never bridge both OLED banks.

The assembly silkscreen intentionally omits individual diode and LED numbers
to keep both faces legible. Align each diode's cathode band with the nearby
silkscreen bar, and align LED pin 1 with the nearby silkscreen triangle.
The LED triangle sits immediately outside the offset pin-1 solder pad; it does
not point at the central routed light aperture. The aperture only lets the
reverse-mounted LED shine through the PCB, while the triangle identifies the
electrical package orientation during soldering. Reference designators remain
available in KiCad and the BOM.

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
  the placement transform: B.Cu/left is +10/+30/+45/+55 degrees and F.Cu/right
  is -10/-30/-45/-55 degrees;
- at least 0.5 mm nominal clearance between adjacent conservative 18 x 18 mm
  thumb-keycap envelopes at the 21.25 mm centers;
- the refined final center step and T3/T4 rotations, including more than 3.4 mm
  nominal clearance between the specified 16.5 mm T3 and T4 keycaps;
- all required controller, matrix, encoder, OLED, RGB, and TRRS nets;
- Helios face labels and isolated high/low D4 header-position detection;
- one 28-LED data chain per assembled half;
- zero unrouted connections; and
- zero shorts, crossings, copper/hole/mask/silkscreen clearance violations.

KiCad reports no DRC warnings, including no dangling tracks or vias. The
verifier rejects any new warning and connectivity analysis reports zero
unrouted nets.

The fabrication audit additionally pins 0.20 mm minimum tracks, approved
0.40/0.20 mm and 0.60/0.30 mm tented-via profiles, and at least 0.25 mm of
annular ring around every plated component hole. The encoder's two mechanical
slot pads were widened from 3.20 to 3.30 mm so they meet that annular-ring
target instead of relying on a 0.20 mm ring.

Two component-level risks remain outside what KiCad DRC can prove:

- The PCB has a 47 uF RGB bulk capacitor and local 100 nF bypassing for the
  level shifter, but no bypass capacitor at each SK6812MINI-E. The LED
  manufacturer's application circuit calls inter-LED capacitance essential.
  Treat RGB as prototype-only, keep the firmware brightness limit at 32, and
  qualify a fully populated half before a larger order. Eliminating this risk
  requires a material footprint/routing revision to add 28 capacitors per
  half.
- The specified encoder is now a generic clickable EC11 matching Keebio's
  20-detent, 20 mm T18-shaft part. The PCB uses the corresponding
  `RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm-keebio_modified` footprint.
  Because EC11 variants differ, dry-fit the exact supplier part and verify one
  firmware event per detent before soldering both boards.

The custom reversible footprints do not all carry complete courtyard data, so
the first pair must still be dry-fitted with the exact Helios headers, OLED,
TRRS jack, hotswap sockets, LEDs, encoder, plate, and case. The repository's
explicit geometry checks cover the known Alpha failures but cannot validate a
supplier substitution's plastic body or connector mouth.

Run:

```sh
npm run verify
```

The board is design-checked, not hardware-proven. Order a small prototype
quantity, follow `hardware/BRING-UP-CHECKLIST.md`, and do not call the revision
production-ready until an assembled pair passes the physical and electrical
bring-up tests. The complete pair BOM is `hardware/BOM-REV-GAMMA.csv`.
