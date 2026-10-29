# Arc 58 Gamma-D — direct RGB prototype

This variant removes the board-mounted U2 level shifter. It is a prototype for electrical qualification, not a production-qualified release. The original Gamma board is retained in the repository.

## Circuit

RP2040 GPIO0 / Pro Micro D3 / U1 pad 1 → RGB_MCU → R1 pad 1 → 330 ohm → R1 pad 2 → RGB_LED_IN → SW1 LED DIN pin 4 → remaining LED chain.

U2 and its footprint are removed. Copper replaces the U2 input/output connection. Obsolete supply/ground branch stubs were cleaned up and zones refilled. R1 remains 0603, nominal 330 ohm; 220 ohm is an acceptable substitute. No user-installed bypass jumper is needed. Do not substitute 10 kohm.

C1 remains available as an additional 100 nF supply bypass capacitor; it is optional for this direct variant. Populate C2, 47 uF / 10 V ceramic / 1206, for bulk RGB supply bypassing. The existing board still lacks per-LED bypass capacitors. LEDs remain on the 5 V rail. Existing firmware continues to use D3/GPIO0, and its brightness limit remains 32.

All other component positions and pad connections are unchanged. Existing plate and case geometry are retained. Silkscreen identifies this variant as GAMMA-D. BOM quantities cover both halves.

## How comparable keyboards avoid U2

The original Sofle RGB build guide specifies an ATmega32U4 Pro Micro or Elite-C. The usual 5 V versions already output 5 V logic, so they do not need a separate 3.3-to-5 V buffer. Using an RP2040 replacement changes this assumption.

Some 5 V addressable LEDs accept 3.3 V data in practice. Adafruit documents this behavior, including SK6812 devices, but it depends on device type, individual tolerances and operating conditions. A working prototype is useful evidence, not a guarantee for every future LED batch.

A design with guaranteed input compatibility can instead use an exact LED part whose specified input-high threshold accepts the controller's guaranteed output-high level, or obtain a shifted signal from a suitable controller pin. Neither is assumed in this variant. GPIO0 on the currently targeted controller remains the data source.

Sources:
- https://josefadamcik.github.io/SofleKeyboard/build_guide_rgb.html
- https://learn.adafruit.com/adafruit-neopixel-uberguide/logic-level
- https://docs.qmk.fm/drivers/ws2812

## Verification

- KiCad 10.0.5 DRC: zero violations and zero unconnected items; see DRC.json.
- Compared the original and variant: U2 is the only removed footprint; every remaining footprint position, orientation and pad net is preserved except the intended R1 pad 1 change to RGB_MCU. Both reversible SW1 DIN pads are preserved.
- Full repository structural check is NOT passing: both original Gamma and Gamma-D stop at the same existing D29 placement mismatch (130.839,137.603 mm versus expected 133.593,140.430 mm). This revision does not change D29. Checks after that failure have not run.
- No physical RGB, signal-integrity, temperature, or manufacturing qualification has been performed. No schematic exists in the source repository; this package contains the PCB project and BOM, not a new schematic.

Before ordering a batch, test the original board with the U2 2-to-4 jumper and R1 installed: that implements the same direct-drive concept. Confirm all LEDs on both halves across cold starts, different colors/animations, and normal USB power sources. If unreliable, keep the original buffered design or qualify a specified lower-threshold LED/controller solution.

## Files and repository

Open arc58-gamma-direct.kicad_pro in KiCad. The PCB includes its footprints; external 3D model libraries may be needed for 3D viewing. No Gerber manufacturing package is included.

Repository copy: hardware/kicad/variants/gamma-direct/.

The repository verifier accepts:

    python3 scripts/verify-kicad-board.py --direct-rgb --board hardware/kicad/variants/gamma-direct/arc58-gamma-direct.kicad_pcb

Use KiCad's Python environment for that command. For the DRC:

    kicad-cli pcb drc --format json --output direct-drc.json hardware/kicad/variants/gamma-direct/arc58-gamma-direct.kicad_pcb

The original generate:fab command still targets the original Gamma board.
