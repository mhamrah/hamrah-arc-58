CONVERT_TO = elite_pi
OLED_DRIVER = ssd1306
OLED_TRANSPORT = i2c

# Build with -e ARC58_SPLIT_DEBUG=yes for OLED role/status and serial logs.
ifeq ($(ARC58_SPLIT_DEBUG),yes)
    CONSOLE_ENABLE = yes
    OPT_DEFS += -DARC58_SPLIT_DEBUG -DSERIAL_DEBUG
endif
