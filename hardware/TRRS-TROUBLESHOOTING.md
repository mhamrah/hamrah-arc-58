# Elite-Pi split troubleshooting

The current firmware uses `CONVERT_TO = elite_pi`, RP2040 PIO half-duplex
serial (`vendor`), and the Pro Micro alias `D2`, which maps to Elite-Pi `GP1`.
The board connects that pin to `TP4` and the TRRS tip. `D4` maps to `GP4` and
selects the hand; it does not select the USB/initiator role. The Elite-Pi
converter uses `GP19` to sense USB power and choose the initiator.

No root cause on the assembled keyboard has been confirmed. A QMK
`SPLIT: receiving handshake failed` message means the expected response byte
was not received, including the case where a byte arrived but was incorrect.
It does not prove that the cable or solder joints are faulty. The response
depends on both firmwares agreeing on the split transaction table.

## 1. Establish a matching firmware pair

Flash the **same newly built UF2 to both Elite-Pis**, individually, with TRRS
disconnected. Old files named `arc58-rev-*-default.uf2` in `output/firmware`
are not evidence of the currently checked-in firmware. The local QMK copy
must also be synchronized from this repository before building.

The diagnostic build preserves the default keymap and serial settings, enables
QMK serial console errors, displays role/link status on the OLED, and initially
turns RGB off without changing EEPROM. Build in the QMK checkout:

```sh
qmk compile -kb hamrah/arc58 -km default -e ARC58_SPLIT_DEBUG=yes
```

The build produces `hamrah_arc58_default.uf2`; save it under a distinct name
before making a normal build. The prepared copy for this investigation is
`output/firmware/arc58-elite-pi-split-debug.uf2`.

With each half connected to USB on its own, verify keys work and the OLED
identifies the correct LEFT/RIGHT hand. Each should say `ROLE: INITIATOR`.
`LINK: DOWN` is expected with no partner. The initial link indication is not
proof of communication; wait several seconds for failed attempts to settle.

## 2. Test with one USB connection

Disconnect USB before inserting or removing TRRS. Connect the two halves,
then connect USB to only one half. Never connect two USB supplies while TRRS
is connected. After several seconds, expect:

| Half | Expected display |
| --- | --- |
| USB-connected | `ROLE: INITIATOR`, `LINK: UP` |
| TRRS-powered | `ROLE: TARGET`, `LINK: SEE INITIATOR` |

Only the initiator tracks failed transactions; the target's local connection
flag cannot prove a successful link. Run `qmk console` to see serial failures
and a status line every two seconds from the USB-connected controller. Status
lines include hand, role, GP4 hand input, and GP19 USB sense; no keystrokes are
logged by this diagnostic code.

- **Both say INITIATOR:** the partner is choosing the wrong role. With only
  one USB cable attached, investigate its USB-sense signal, power wiring, and
  controller identity. Testing `SPLIT_USB_DETECT` (USB enumeration instead of
  voltage sense) is a targeted next experiment, not a confirmed fix.
- **Partner stays blank:** measure its power rails before assuming it is dead;
  an unconfigured or absent OLED is also blank.
- **INITIATOR/TARGET are correct but LINK stays DOWN:** check end-to-end GP1
  continuity and shorts, then capture the exact serial errors.
- **Both show the same hand:** check GP4 and the R4/R5 hand resistors. Wrong
  handedness causes matrix mapping problems but is separate from role selection.
- **Works only with RGB off:** investigate voltage drop/current draw under
  load. Do not change serial wiring to address a power problem.

Repeat after moving the single USB connection to the other half, with power
off while changing connections.

## 3. Measure the actual assembled path

These are the expected connections for the current PCB. Confirm the fabricated
revision before applying them to an older board. With **all power disconnected**
and TRRS fully inserted, check low resistance through the whole path:

| Path | Expected |
| --- | --- |
| Elite-Pi GP1 → local TP4 → local jack tip | Continuity |
| Left GP1 → right GP1 (including cable and both sockets) | Continuity |
| Left TP1 → right TP1 | Ground continuity |
| Left TP2 → right TP2 | Shared supply continuity |

Check that GP1/TP4 is not shorted to ground or the supply. Check cable contacts
directly for a straight-through four-conductor TRRS connection; a working
audio cable is not sufficient evidence. PCB contact assignments are tip=data,
ring 1=spare, ring 2=supply, sleeve=ground. If the installed jack differs from
MJ-4PP-9, verify its contact geometry with a meter rather than its appearance.

With the cable already installed and only one USB connection, measure on the
partner relative to TP1: TP2 should be about 5 V (allowing controller/cable
drop), TP3 about 3.3 V. The serial line uses 3.3 V logic; **do not add a pull-up
to 5 V**. QMK's RP2040 PIO half-duplex driver does not require an external
pull-up. A meter cannot validate serial pulses; use a scope or logic analyzer
at both TP4 pads if continuity, roles, and firmware all check out.

If a clean data path still fails, a controlled follow-up is to lower serial
speed on both halves together (`SELECT_SOFT_SERIAL_SPEED=2`, 115200 baud,
versus the default 230400). Changing timeouts or speed before these checks
can hide the actual failure.

## Repository inspection, 2026-09-26

- Main revision: `7bbec0d`; local QMK revision recorded alongside built UF2s.
- Pin aliases and serial driver match the PCB's intended GP1 single-wire path.
- KiCad DRC: zero violations and zero unconnected items. This checks the design
  file, not solder joints, the cable, physical jack contacts, or a fabricated PCB.
- `npm run verify:pcb` fails on an existing D29 placement assertion (actual
  130.839,137.603 versus expected 133.593,140.430). It exits before later
  electrical assertions and is not evidence of a TRRS fault.

References: [Elite-Pi usage guide](https://docs.keeb.io/elite-pi-guide),
[QMK serial driver](https://docs.qmk.fm/drivers/serial),
[QMK split configuration](https://docs.qmk.fm/features/split_keyboard).
