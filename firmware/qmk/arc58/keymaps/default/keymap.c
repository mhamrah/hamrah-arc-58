// SPDX-License-Identifier: GPL-2.0-or-later

#include QMK_KEYBOARD_H

enum layers { BASE, NAV };

/* The matrix deliberately mirrors the two physical 5x6 halves. */
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [BASE] = {
        {KC_ESC,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T   },
        {KC_TAB,  KC_A,    KC_S,    KC_D,    KC_F,    KC_G   },
        {KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B   },
        {KC_LCTL, KC_LALT, KC_LGUI, KC_NO,   KC_NO,   KC_NO  },
        {KC_SPC,  MO(NAV), KC_ENT,  KC_BSPC, KC_MUTE, KC_NO  },
        {KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,    KC_MINS},
        {KC_H,    KC_J,    KC_K,    KC_L,    KC_SCLN, KC_QUOT},
        {KC_N,    KC_M,    KC_COMM, KC_DOT,  KC_SLSH, KC_RSFT},
        {KC_NO,   KC_NO,   KC_NO,   KC_RALT, KC_RCTL, KC_NO  },
        {KC_DEL,  KC_SPC,  KC_ENT,  MO(NAV), KC_MUTE, KC_NO  },
    },
    [NAV] = {
        {QK_BOOT, KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO  },
        {KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO  },
        {KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO  },
        {KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO  },
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_NO  },
        {KC_NO,   KC_HOME, KC_UP,   KC_END,  KC_PGUP, KC_NO  },
        {KC_LEFT, KC_DOWN, KC_RGHT, KC_NO,   KC_PGDN, KC_NO  },
        {KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO  },
        {KC_NO,   KC_NO,   KC_NO,   KC_TRNS, KC_TRNS, KC_NO  },
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_NO  },
    },
};

bool encoder_update_user(uint8_t index, bool clockwise) {
    if (index == 0) {
        tap_code(clockwise ? KC_VOLU : KC_VOLD);
    }
    return false;
}

#ifdef OLED_ENABLE
oled_rotation_t oled_init_user(oled_rotation_t rotation) {
    return is_keyboard_left() ? OLED_ROTATION_0 : OLED_ROTATION_180;
}

bool oled_task_user(void) {
    oled_write_ln_P(PSTR("HAMRAH"), false);
    oled_write_ln_P(PSTR("ARC 58"), false);
    oled_write_ln_P(is_keyboard_left() ? PSTR("LEFT") : PSTR("RIGHT"), false);
    oled_write_ln_P(get_highest_layer(layer_state) == NAV ? PSTR("NAV") : PSTR("BASE"), false);
    return false;
}
#endif
