# Arc 58 Rev Beta bring-up checklist

Do not connect the two halves together or connect a computer until the first
three inspections pass. This checklist is the acceptance gate for calling the
hardware prototype working.

## 1. Before power

- Inspect every SK6812MINI-E orientation against the PCB pin-1 marking.
- Confirm all 28 routed RGB apertures are open and centered under their switch;
  reject any panel with a missing aperture or an unremoved routing tab.
- Confirm every diode has its cathode band aligned with the PCB cathode mark.
- Confirm the 74AHCT1G125 orientation and that its `/OE` pad is tied to GND.
- With a meter, verify `VCC` to `GND` is not shorted on each unpowered half.
- Verify the TRRS cable straight through: sleeve is `GND`, ring 2 is `VBUS`,
  tip is `SPLIT_DATA`, and ring 1 is the unused spare. There are no crossed
  TX/RX conductors in this one-wire split design.
- Dry-fit the TRRS plug and confirm it reaches full insertion through the
  inner-edge 10 mm plate/case opening without touching the encoder.
- Confirm B.Cu faces the keycaps on the left half and F.Cu faces the keycaps
  on the right half; sockets, diodes, and LEDs belong on each half's underside.
- Dry-fit all four thumb switches on each face against the 1:1 paper/plate
  template. The B.Cu/left axes must fan +10/+30/+45/+55 degrees and the
  F.Cu/right axes must mirror to -10/-30/-45/-55 degrees. Confirm the 21.25 mm
  centers leave visible clearance between all four installed Choc v1 keycaps.
- Fit the 18 mm encoder knob and confirm it leaves approximately 9.17 mm of
  free space to both the nearest C6 cap and the curved inner PCB edge. Confirm
  the relocated H4 fastener and boss do not obstruct finger access.
- Confirm the Helios uses only the `L`-marked header holes on the B.Cu/left
  face or the `R`-marked holes on the F.Cu/right face.
- Confirm R4 and R5 are populated on both PCBs; there is no hand-select jumper.
- With the Helios removed and power disconnected, measure approximately 10
  kohm from the `L`-position D4 hole to `TP3` (`3V3`) and approximately 10
  kohm from the `R`-position D4 hole to `TP1` (`GND`). Confirm neither D4 hole
  is shorted to the opposite rail and the two D4 holes are isolated.
- Bridge front `JP1-JP4` on the left and back `JP5-JP8` on the right. The
  selected jumper bank is opposite the OLED face; never bridge both banks.

## 2. One-half power test

Connect USB to the left half only, with no TRRS cable attached.

- Verify 5 V at `TP2` and ground at `TP1`.
- Verify the Helios enumerates as a USB keyboard after flashing.
- Hold/reset the Helios to enter UF2 boot mode and copy the compiled firmware.
- Check all 29 inputs with a keyboard tester: 28 Choc switches plus encoder
  press. Check encoder clockwise/counter-clockwise events separately.
- Start RGB Matrix at the supplied brightness limit of 32. Verify all 28 local
  LEDs in sequence, then measure USB current with white enabled. Do not raise
  the brightness until the measured current is safe for the cable and USB port.

Repeat for the right half alone.

## 3. Split test

Unplug USB, attach the TRRS cable, then connect USB to the left half only.

- Verify 5 V at the right half `TP2`.
- Verify keys and encoder events from both halves reach the host.
- Verify RGB Matrix reports and controls both 28-LED chains.
- Disconnect USB before removing the TRRS cable. Never attach USB to both
  halves while the TRRS cable is installed.

## Firmware commands

Inside a QMK firmware checkout containing `firmware/qmk/arc58` at
`keyboards/hamrah/arc58`:

```sh
qmk lint -kb hamrah/arc58
qmk compile -kb hamrah/arc58 -km default
```

The build creates `hamrah_arc58_default.uf2`. Place each Helios in its UF2
bootloader mode and copy the same file to both mounted drives. The populated
header position determines left/right automatically. The supplied default
is a usable QWERTY plus navigation-layer keymap; customize it only after this
checklist passes.

## Acceptance record

Record the build commit, controller revision, TRRS cable used, measured idle
and RGB current, and any failed matrix/LED position. The board is not verified
working until every check above passes on the assembled pair.
