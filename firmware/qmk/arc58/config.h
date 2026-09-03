// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

// D2 split serial and D4 handedness are declared in keyboard.json. The two
// physical controller header positions isolate D4: the L position has a 10k pull-up
// and the R position has a 10k pull-down. QMK's default high=left/low=right
// polarity therefore selects the correct hand automatically with one UF2.
#define I2C1_SDA_PIN D1
#define I2C1_SCL_PIN D0
#define RGB_MATRIX_MAXIMUM_BRIGHTNESS 32
#define RGB_MATRIX_DEFAULT_ON true
#define RGB_MATRIX_DEFAULT_VAL 32
#define RGB_MATRIX_DEFAULT_MODE RGB_MATRIX_DUAL_BEACON
#define RGB_MATRIX_DEFAULT_SAT 128
#define RGB_MATRIX_DEFAULT_HUE 64
#define RGB_MATRIX_DEFAULT_SPD 64
#define RGB_MATRIX_SLEEP

// Elite-Pi has no onboard status/power LED.
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
