// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

// D2 split serial and D4 handedness are declared in keyboard.json. The two
// physical Helios header positions isolate D4: the L position has a 10k pull-up
// and the R position has a 10k pull-down. QMK's default high=left/low=right
// polarity therefore selects the correct hand automatically with one UF2.
#define I2C1_SDA_PIN D1
#define I2C1_SCL_PIN D0
#define RGB_MATRIX_MAXIMUM_BRIGHTNESS 32
#define RGB_MATRIX_DEFAULT_VAL 32
