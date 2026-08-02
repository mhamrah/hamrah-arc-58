# Hamrah Arc 58

Firmware definition for the wired, TRRS-split Arc 58 keyboard using two
KEEBD Helios (RP2040) controllers. Build it with `qmk compile -kb
hamrah/arc58 -km default`; `CONVERT_TO = helios` selects the Helios target.

The definition was linted and compiled successfully against upstream QMK
`d6235b96` (QMK 0.33.12) on 2026-08-02. The resulting local build is written
to `output/firmware/arc58-rev-alpha-default.uf2` and can be copied to either
Helios while it is in RP2040 bootloader mode.

The default keymap is a usable QWERTY layout with a momentary navigation layer,
`QK_BOOT` at left Escape on that layer, and volume encoders. Verify every
physical position with the project-level bring-up checklist before relying on
it as a daily driver.
