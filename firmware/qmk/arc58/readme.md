# Hamrah Arc 58

Firmware definition for the wired, TRRS-split Arc 58 keyboard using two
Keebio Elite-Pi (RP2040) controllers. Build it with `qmk compile -kb
hamrah/arc58 -km default`; `CONVERT_TO = elite_pi` selects the Elite-Pi target.

The definition was linted and compiled successfully against upstream QMK
`d6235b96` (QMK 0.33.12) on 2026-08-02. The resulting local build is written
to `output/firmware/hamrah_arc58_default.uf2` and can be copied to either
Elite-Pi while it is in RP2040 bootloader mode.

The default keymap matches the Sofle/mhamrah Mac layout, with Main, Symbols,
and Util layers, RGB controls, and volume/page encoders. Elite-Pi controllers
have no onboard power or status LED.

For split failures, build with `-e ARC58_SPLIT_DEBUG=yes` to show hand,
initiator/target role, and initiator connection status on the OLED and enable
serial error logs in `qmk console`. RGB starts off in this diagnostic build.
Flash the identical diagnostic UF2 to both controllers. See
[`hardware/TRRS-TROUBLESHOOTING.md`](../../../hardware/TRRS-TROUBLESHOOTING.md)
for the measurement sequence and interpretation.
