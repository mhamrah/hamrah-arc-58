// Hamrah ARC-58 keymap, based on keyboards/sofle_choc/keymaps/mhamrah.

#include QMK_KEYBOARD_H

enum layers { MAC_DEFAULT, MAC_SYMBOLS, MAC_UTIL };
enum custom_keycodes { RGB_NEXT = SAFE_RANGE };

#define RGB_PREV QK_RGB_MATRIX_MODE_PREVIOUS
#define RGB_HUI  QK_RGB_MATRIX_HUE_UP
#define RGB_HUD  QK_RGB_MATRIX_HUE_DOWN
#define RGB_SAI  QK_RGB_MATRIX_SATURATION_UP
#define RGB_SAD  QK_RGB_MATRIX_SATURATION_DOWN
#define RGB_VAI  QK_RGB_MATRIX_VALUE_UP
#define RGB_VAD  QK_RGB_MATRIX_VALUE_DOWN
#define RGB_SPI  QK_RGB_MATRIX_SPEED_UP
#define RGB_SPD  QK_RGB_MATRIX_SPEED_DOWN

void keyboard_post_init_user(void) {
    // Always provide a visible power-on indication, even if RGB was previously
    // turned off and that state was saved in EEPROM.
    rgb_matrix_enable_noeeprom();
}

/*
 * Rows 0-4 are the left half and rows 5-9 are the right half. The right
 * half is electrical matrix order, matching QMK's Sofle LAYOUT macro.
 */
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [MAC_DEFAULT] = {
        {KC_GRV,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5},
        {KC_TAB,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T},
        {KC_RCTL, KC_A,    KC_S,    KC_D,    KC_F,    KC_G},
        {KC_LSFT, KC_B,    KC_Z,    KC_X,    KC_C,    KC_V},
        {RGB_NEXT, LSA_T(KC_TAB), LOPT_T(KC_ESC), MO(MAC_SYMBOLS), LCMD_T(KC_SPC), KC_MUTE},
        {KC_MINS, KC_0,    KC_9,    KC_8,    KC_7,    KC_6},
        {KC_EQL,  KC_P,    KC_O,    KC_I,    KC_U,    KC_Y},
        {KC_QUOT, KC_SCLN, KC_L,    KC_K,    KC_J,    KC_H},
        {KC_RSFT, KC_SLSH, KC_DOT,  KC_COMM, KC_M,    KC_N},
        {SCMD(KC_SPC), MO(MAC_UTIL), LCTL_T(KC_TAB), KC_ENT, KC_SPC, KC_MPLY},
    },
    [MAC_SYMBOLS] = {
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
        {KC_TRNS, KC_TRNS, KC_PGDN, KC_PGUP, KC_TRNS, KC_TRNS},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
        {KC_ESC,  KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
        {KC_TRNS, KC_RBRC, KC_LBRC, KC_RPRN, KC_LPRN, KC_TRNS},
        {KC_BSLS, KC_RGHT, KC_UP,   KC_DOWN, KC_LEFT, KC_TRNS},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_BSPC, KC_TRNS},
    },
    [MAC_UTIL] = {
        {RGB_NEXT, KC_F1,   KC_F2,   KC_F3,   KC_F4,   KC_F5},
        {RGB_NEXT, RGB_HUI, RGB_SAI, RGB_VAI, RGB_SPI, KC_F11},
        {RGB_PREV, RGB_HUD, RGB_SAD, RGB_VAD, RGB_SPD, KC_TRNS},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, RGB_NEXT},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
        {QK_BOOT, KC_F10,  KC_F9,   KC_F8,   KC_F7,   KC_F6},
        {EE_CLR,   KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_F12},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
        {KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS, KC_TRNS},
    },
};

#if defined(ENCODER_MAP_ENABLE)
const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {
    [MAC_DEFAULT] = {ENCODER_CCW_CW(KC_VOLD, KC_VOLU), ENCODER_CCW_CW(KC_PGDN, KC_PGUP)},
    [MAC_SYMBOLS] = {ENCODER_CCW_CW(KC_TRNS, KC_TRNS), ENCODER_CCW_CW(KC_TRNS, KC_TRNS)},
    [MAC_UTIL] = {ENCODER_CCW_CW(RGB_PREV, RGB_NEXT), ENCODER_CCW_CW(RGB_HUD, RGB_HUI)},
};
#endif

bool process_record_user(uint16_t keycode, keyrecord_t *record) {
    if (keycode == RGB_NEXT && record->event.pressed) {
        if (!rgb_matrix_is_enabled()) {
            rgb_matrix_enable();
            rgb_matrix_mode(RGB_MATRIX_SOLID_COLOR);
        } else {
            switch (rgb_matrix_get_mode()) {
                case RGB_MATRIX_SOLID_COLOR:       rgb_matrix_mode(RGB_MATRIX_CYCLE_UP_DOWN); break;
                case RGB_MATRIX_CYCLE_UP_DOWN:     rgb_matrix_mode(RGB_MATRIX_CYCLE_OUT_IN); break;
                case RGB_MATRIX_CYCLE_OUT_IN:      rgb_matrix_mode(RGB_MATRIX_CYCLE_PINWHEEL); break;
                case RGB_MATRIX_CYCLE_PINWHEEL:    rgb_matrix_mode(RGB_MATRIX_DUAL_BEACON); break;
                case RGB_MATRIX_DUAL_BEACON:       rgb_matrix_mode(RGB_MATRIX_RAINBOW_PINWHEELS); break;
                case RGB_MATRIX_RAINBOW_PINWHEELS: rgb_matrix_mode(RGB_MATRIX_HUE_BREATHING); break;
                case RGB_MATRIX_HUE_BREATHING:     rgb_matrix_disable(); break;
                default:                           rgb_matrix_mode(RGB_MATRIX_SOLID_COLOR); break;
            }
        }
        return false;
    }
    return true;
}

#ifdef OLED_ENABLE
oled_rotation_t oled_init_user(oled_rotation_t rotation) {
    return is_keyboard_left() ? OLED_ROTATION_0 : OLED_ROTATION_180;
}

bool oled_task_user(void) {
    oled_write_ln_P(PSTR("HAMRAH ARC58"), false);
    oled_write_ln_P(is_keyboard_left() ? PSTR("LEFT") : PSTR("RIGHT"), false);
    uint8_t layer = get_highest_layer(layer_state);
    oled_write_ln_P(layer == MAC_UTIL ? PSTR("UTIL") : layer == MAC_SYMBOLS ? PSTR("SYMS") : PSTR("MAIN"), false);
    return false;
}
#endif
