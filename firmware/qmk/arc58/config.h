// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

// D2 split serial and D4 handedness are declared in keyboard.json. QMK's
// default handedness polarity is high=left and low=right, so JP_HAND must
// bridge 1-2 (D4 to 3V3) on the left PCB or 2-3 (D4 to GND) on the right PCB.
#define I2C1_SDA_PIN D1
#define I2C1_SCL_PIN D0
#define RGB_MATRIX_MAXIMUM_BRIGHTNESS 32
#define RGB_MATRIX_DEFAULT_VAL 32
