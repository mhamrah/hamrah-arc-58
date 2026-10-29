#!/usr/bin/env python3
"""Electrical and structural checks for the canonical reversible Arc 58 PCB."""

from pathlib import Path
import json
import math
import re
import pcbnew
import argparse


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "kicad" / "arc58-reversible.kicad_pcb"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--board", type=Path, default=BOARD)
parser.add_argument("--direct-rgb", action="store_true", help="Check the Gamma-D direct RGB prototype")
args = parser.parse_args()
BOARD = args.board
LAYOUT = ROOT / "layout.config.json"
FIRMWARE = ROOT / "firmware" / "qmk" / "arc58"
SWITCH_FOOTPRINT = (
    ROOT
    / "hardware"
    / "kicad"
    / "arc58-reversible.pretty"
    / "Sofle_Choc_Hotswap_SK6812MINI-E_Reversible.kicad_mod"
)
KEY_SWITCHES = list(range(1, 25)) + list(range(26, 30))


def fail(message):
    raise SystemExit(f"FAIL: {message}")


def pad(footprint, number):
    """Return one physical pad; reversible footprints duplicate pad numbers."""
    return next(
        (item for item in footprint.Pads() if item.GetNumber() == str(number)),
        None,
    )


def net(footprint, number):
    item = pad(footprint, number)
    if item is None:
        fail(f"{footprint.GetReference()}: missing pad {number}")
    return item.GetNetname()


def close(actual, expected, tolerance=0.002):
    return abs(actual - expected) <= tolerance


def position_mm(footprint):
    point = footprint.GetPosition()
    return pcbnew.ToMM(point.x), pcbnew.ToMM(point.y)


def check_placement(footprint, expected_x, expected_y, expected_rotation):
    actual_x, actual_y = position_mm(footprint)
    actual_rotation = footprint.GetOrientationDegrees() % 360
    expected_rotation %= 360
    rotation_delta = abs((actual_rotation - expected_rotation + 180) % 360 - 180)
    if not (
        # Sofle's original matrix locations alternate on a 0.05/0.10 mm
        # grid, so accept only that sub-manufacturing-tolerance rounding.
        close(actual_x, expected_x, 0.051)
        and close(actual_y, expected_y, 0.051)
        and rotation_delta <= 0.01
    ):
        fail(
            f"{footprint.GetReference()}: placement {actual_x:.3f},"
            f"{actual_y:.3f} @ {actual_rotation:.2f} does not match approved "
            f"layout {expected_x:.3f},{expected_y:.3f} @ {expected_rotation:.2f}"
        )


board = pcbnew.LoadBoard(str(BOARD))
layout = json.loads(LAYOUT.read_text())
keyboard = json.loads((FIRMWARE / "keyboard.json").read_text())
if board.GetCopperLayerCount() != 2:
    fail("expected a two-layer PCB")

footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
required = {
    "U1", "U2", "R1", "R2", "R3", "R4", "R5", "C1", "C2", "J1", "J2",
    "RST1", "SW25",
}
if args.direct_rgb:
    required.discard("U2")
    if "U2" in footprints:
        fail("direct RGB variant must not contain U2")
required.update(f"H{i}" for i in range(1, 7))
required.update(f"TP{i}" for i in (1, 2, 3, 4, 6, 7, 8))
required.update(f"JP{i}" for i in range(1, 9))
required.update(f"SW{i}" for i in KEY_SWITCHES)
required.update(f"D{i}" for i in range(1, 30))
missing = sorted(required - footprints.keys())
if missing:
    fail(f"missing footprints: {', '.join(missing)}")
obsolete = sorted({"JP_HAND", "TP5"} & footprints.keys())
if obsolete:
    fail(f"obsolete manual-handedness footprints remain: {', '.join(obsolete)}")


def item_distance(first, second):
    return math.hypot(first.x - second.x, first.y - second.y)


def pad_on_layer(footprint, number, layer):
    return next(
        (
            item for item in footprint.Pads()
            if item.GetNumber() == str(number) and item.IsOnLayer(layer)
        ),
        None,
    )


# Keep the reversible assembly silkscreen useful without covering the board in
# designators. Each diode gets only a cathode bar; each RGB LED gets only a
# local triangle beside pin 1. Reference numbers remain available in KiCad and
# the BOM but are intentionally absent from both visible silkscreen faces.
for drawing in board.GetDrawings():
    if not isinstance(drawing, pcbnew.PCB_TEXT):
        continue
    text = drawing.GetText()
    if re.fullmatch(r"D\d+", text) or re.fullmatch(r"LED\d+ 1>", text):
        fail(f"busy component designator remains on silkscreen: {text}")

for drawing in board.GetDrawings():
    if (
        type(drawing).__name__ != "PCB_SHAPE"
        or drawing.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS)
        or drawing.GetShapeStr() != "Line"
    ):
        continue
    start, end = drawing.GetStart(), drawing.GetEnd()
    dimensions = (
        round(
            math.hypot(
                pcbnew.ToMM(end.x - start.x),
                pcbnew.ToMM(end.y - start.y),
            ),
            3,
        ),
        round(pcbnew.ToMM(drawing.GetWidth()), 3),
    )
    if dimensions in {(1.0, 0.22), (1.4, 0.18)}:
        fail("legacy board-level diode/LED silkscreen bar remains")

for diode_number in range(1, 30):
    diode = footprints[f"D{diode_number}"]
    markers = [
        item for item in diode.GraphicalItems()
        if item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)
    ]
    if len(markers) != 2 or any(item.GetShapeStr() != "Line" for item in markers):
        fail(f"D{diode_number}: expected one cathode bar on each silkscreen face")
    for marker in markers:
        copper_layer = pcbnew.F_Cu if marker.GetLayer() == pcbnew.F_SilkS else pcbnew.B_Cu
        cathode = pad_on_layer(diode, "1", copper_layer)
        anode = pad_on_layer(diode, "2", copper_layer)
        if cathode is None or anode is None:
            fail(f"D{diode_number}: reversible diode pads are incomplete")
        center = marker.GetCenter()
        if item_distance(center, cathode.GetPosition()) >= item_distance(center, anode.GetPosition()):
            fail(f"D{diode_number}: cathode bar is not on the pad-1 side")

for switch_number in KEY_SWITCHES:
    switch = footprints[f"SW{switch_number}"]
    markers = [
        item for item in switch.GraphicalItems()
        if item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)
    ]
    if len(markers) != 2 or any(item.GetShapeStr() != "Polygon" for item in markers):
        fail(f"SW{switch_number}: expected one LED pin-1 triangle on each silkscreen face")
    if any(
        isinstance(item, pcbnew.PCB_TEXT) and item.GetText() == "LED PIN 1"
        for item in switch.GraphicalItems()
    ):
        fail(f"SW{switch_number}: ambiguous LED Fab-layer text remains")
    for marker in markers:
        copper_layer = pcbnew.F_Cu if marker.GetLayer() == pcbnew.F_SilkS else pcbnew.B_Cu
        pin_one = pad_on_layer(switch, "1", copper_layer)
        other_pads = [pad_on_layer(switch, number, copper_layer) for number in (2, 3, 4)]
        if pin_one is None or any(item is None for item in other_pads):
            fail(f"SW{switch_number}: reversible RGB pads are incomplete")
        center = marker.GetCenter()
        pin_one_distance = item_distance(center, pin_one.GetPosition())
        if pcbnew.ToMM(pin_one_distance) > 1.6:
            fail(f"SW{switch_number}: LED triangle is not adjacent to pin 1")
        if any(pin_one_distance >= item_distance(center, item.GetPosition()) for item in other_pads):
            fail(f"SW{switch_number}: LED triangle is not closest to pin 1")

switch_footprint_source = SWITCH_FOOTPRINT.read_text()
if "LED PIN 1" in switch_footprint_source or switch_footprint_source.count("(fp_poly") != 2:
    fail("switch footprint library is not synchronized with the board's pin-1 triangles")

rgb = layout["rgb"]
if len(KEY_SWITCHES) != rgb["ledsPerHalf"]:
    fail("layout RGB LED count does not match the key-switch footprints")
expected_aperture_lengths = sorted([
    rgb["apertureWidth"], rgb["apertureWidth"],
    rgb["apertureHeight"], rgb["apertureHeight"],
])
for switch_number in KEY_SWITCHES:
    switch = footprints[f"SW{switch_number}"]
    aperture = [
        item for item in switch.GraphicalItems()
        if item.GetLayer() == pcbnew.Edge_Cuts
    ]
    if len(aperture) != 4 or any(item.GetShapeStr() != "Line" for item in aperture):
        fail(f"SW{switch_number}: expected one four-segment RGB aperture")
    actual_lengths = sorted(
        pcbnew.ToMM((item.GetEnd() - item.GetStart()).EuclideanNorm())
        for item in aperture
    )
    if any(
        not close(actual, expected)
        for actual, expected in zip(actual_lengths, expected_aperture_lengths)
    ):
        fail(f"SW{switch_number}: RGB aperture dimensions are wrong")
    endpoints = {}
    for item in aperture:
        for point in (item.GetStart(), item.GetEnd()):
            key = (round(pcbnew.ToMM(point.x), 3), round(pcbnew.ToMM(point.y), 3))
            endpoints[key] = endpoints.get(key, 0) + 1
    if len(endpoints) != 4 or set(endpoints.values()) != {2}:
        fail(f"SW{switch_number}: RGB aperture is not a closed rectangle")

# Prove that the routed PCB still uses the approved geometry.  The canonical
# board is the horizontal mirror of the left-half layout, which is what makes
# one physical PCB usable for both hands when populated on opposite faces.
transform = layout["manufacturing"]["pcbTransform"]
if not transform["mirrorX"]:
    fail("manufacturing transform must mirror the reversible PCB")


def pcb_location(x, y, rotation=0):
    return (
        transform["originX"] - x,
        transform["originY"] + y,
        transform["rotationBase"] + rotation,
    )


def undirected_axis_angle(first, second):
    """Return a physical switch axis in the range [-90, 90) degrees."""
    angle = math.degrees(math.atan2(second.y - first.y, second.x - first.x))
    return (angle + 90) % 180 - 90


def check_reversible_thumb_axis(footprint, left_rotation):
    """Prove the assembled F/right and mirrored B/left switch handedness.

    KiCad's footprint rotation number alone is not sufficient here: the Rev
    Alpha regression came from comparing it to the same incorrect transform.
    The two 1.8 mm switch-locator holes expose the physical key axis directly.
    """
    locator_holes = [
        item for item in footprint.Pads()
        if item.GetNumber() == ""
        and close(pcbnew.ToMM(item.GetDrillSize().x), 1.8)
        and close(pcbnew.ToMM(item.GetDrillSize().y), 1.8)
    ]
    if len(locator_holes) != 2:
        fail(f"{footprint.GetReference()}: expected two 1.8 mm locator holes")
    first, second = (item.GetPosition() for item in locator_holes)
    front_axis = undirected_axis_angle(first, second)
    back_axis = -front_axis
    if not close(front_axis, -left_rotation, 0.01):
        fail(
            f"{footprint.GetReference()}: F-side/right physical axis "
            f"{front_axis:.2f} must be {-left_rotation:.2f} degrees"
        )
    if not close(back_axis, left_rotation, 0.01):
        fail(
            f"{footprint.GetReference()}: B-side/left physical axis "
            f"{back_axis:.2f} must be {left_rotation:.2f} degrees"
        )


pitch_x = layout["switch"]["pitchX"]
pitch_y = layout["switch"]["pitchY"]
matrix = layout["matrix"]


def cubic_point(start, control_1, control_2, end, amount):
    inverse = 1 - amount
    return {
        "x": (
            inverse ** 3 * start["x"]
            + 3 * inverse ** 2 * amount * control_1["x"]
            + 3 * inverse * amount ** 2 * control_2["x"]
            + amount ** 3 * end["x"]
        ),
        "y": (
            inverse ** 3 * start["y"]
            + 3 * inverse ** 2 * amount * control_1["y"]
            + 3 * inverse * amount ** 2 * control_2["y"]
            + amount ** 3 * end["y"]
        ),
    }


def outline_crossings_at_y(y, steps=2048):
    outline = layout["mechanical"]["boardOutline"]
    sampled = []
    for index, start in enumerate(outline):
        end = outline[(index + 1) % len(outline)]
        for step in range(steps):
            sampled.append(cubic_point(
                start,
                start["controlOut"],
                end["controlIn"],
                end,
                step / steps,
            ))
    crossings = []
    for index, start in enumerate(sampled):
        end = sampled[(index + 1) % len(sampled)]
        if (
            start["y"] <= y < end["y"]
            or end["y"] <= y < start["y"]
        ):
            amount = (y - start["y"]) / (end["y"] - start["y"])
            crossings.append(start["x"] + amount * (end["x"] - start["x"]))
    if len(crossings) < 2:
        fail(f"board outline does not cross encoder y={y} twice")
    return crossings


for column in range(matrix["columns"]):
    for row in range(matrix["rows"]):
        reference = f"SW{row * matrix['columns'] + (matrix['columns'] - column)}"
        x = column * pitch_x
        y = matrix["columnStagger"][column] + row * pitch_y
        check_placement(footprints[reference], *pcb_location(x, y))

encoder_config = layout["encoder"]
encoder_y = (
    matrix["columnStagger"][encoder_config["alignWithColumn"]]
    + encoder_config["row"] * pitch_y
)
if (
    encoder_config["horizontalPlacement"]
    != "equal-clearance-between-c6-and-inner-edge"
):
    fail("unsupported encoder horizontal-placement contract")
inner_edge_x = max(outline_crossings_at_y(encoder_y))
column_edge_x = (
    (matrix["columns"] - 1) * pitch_x
    + layout["switch"]["keycapWidth"] / 2
)
encoder_x = (column_edge_x + inner_edge_x) / 2
encoder = footprints["SW25"]
check_placement(encoder, *pcb_location(encoder_x, encoder_y))
expected_encoder_footprint = encoder_config["sofleFootprint"].split(":")[-1]
actual_encoder_footprint = str(encoder.GetFPID().GetLibItemName())
if actual_encoder_footprint != expected_encoder_footprint:
    fail(
        f"SW25: expected EC11 footprint {expected_encoder_footprint}, got "
        f"{actual_encoder_footprint}"
    )

column_a, column_b = layout["thumbArc"]["startBetweenColumns"]
thumb_x = (
    ((column_a + column_b) / 2) * pitch_x
    - layout["thumbArc"]["startOffsetTowardOuterEdge"]
)
thumb_y = max(
    matrix["columnStagger"][column_a] + (matrix["rows"] - 1) * pitch_y,
    matrix["columnStagger"][column_b] + (matrix["rows"] - 1) * pitch_y,
) + layout["thumbArc"]["dropFromLowerColumnKey"]
for index in range(layout["thumbArc"]["count"]):
    reference = f"SW{29 - index}"
    rotation = layout["thumbArc"]["keyRotations"][index]
    check_placement(footprints[reference], *pcb_location(thumb_x, thumb_y, rotation))
    check_reversible_thumb_axis(footprints[reference], rotation)
    if index < len(layout["thumbArc"]["segmentAngles"]):
        angle = math.radians(layout["thumbArc"]["segmentAngles"][index])
        thumb_x += layout["thumbArc"]["step"] * math.cos(angle)
        thumb_y += layout["thumbArc"]["step"] * math.sin(angle)

for index, hole_config in enumerate(layout["mechanical"]["mountingHoles"], 1):
    expected_x, expected_y, _ = pcb_location(hole_config["x"], hole_config["y"])
    actual_x, actual_y = position_mm(footprints[f"H{index}"])
    if not (close(actual_x, expected_x) and close(actual_y, expected_y)):
        fail(f"H{index}: mounting-hole placement does not match the plate geometry")

outline = layout["mechanical"]["boardOutline"]
outline_mode = layout["mechanical"].get("outlineCurveMode", "catmull-rom")
if outline_mode == "explicit-bezier":
    if not all("controlIn" in point and "controlOut" in point for point in outline):
        fail("every explicit Bezier outline anchor needs incoming and outgoing handles")
else:
    tension = layout["mechanical"]["outlineCurveTension"]
    if not 0 < tension <= 1:
        fail("outline curve tension must be greater than zero and at most one")


def curve_point(point):
    x, y, _ = pcb_location(point["x"], point["y"])
    return round(x, 3), round(y, 3)


expected_outline_segments = set()
for index, start in enumerate(outline):
    end = outline[(index + 1) % len(outline)]
    if outline_mode == "explicit-bezier":
        control_1 = start["controlOut"]
        control_2 = end["controlIn"]
        incoming = (
            end["x"] - control_2["x"],
            end["y"] - control_2["y"],
        )
        outgoing = (
            end["controlOut"]["x"] - end["x"],
            end["controlOut"]["y"] - end["y"],
        )
        cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
        dot = incoming[0] * outgoing[0] + incoming[1] * outgoing[1]
        if abs(cross) >= 0.01 or dot <= 0:
            fail(f"board outline join {index + 1} is not tangent-continuous")
    else:
        previous = outline[(index - 1) % len(outline)]
        following = outline[(index + 2) % len(outline)]
        control_1 = {
            "x": start["x"] + (end["x"] - previous["x"]) * tension / 6,
            "y": start["y"] + (end["y"] - previous["y"]) * tension / 6,
        }
        control_2 = {
            "x": end["x"] - (following["x"] - start["x"]) * tension / 6,
            "y": end["y"] - (following["y"] - start["y"]) * tension / 6,
        }
    expected_outline_segments.add(
        (*curve_point(start), *curve_point(control_1),
         *curve_point(control_2), *curve_point(end))
    )

actual_outline_segments = set()
for drawing in board.GetDrawings():
    if drawing.GetLayer() != pcbnew.Edge_Cuts:
        continue
    if drawing.GetShapeStr() != "Bezier Curve":
        fail("board outline must contain smooth Bezier curves only")
    points = (
        drawing.GetStart(), drawing.GetBezierC1(), drawing.GetBezierC2(),
        drawing.GetEnd(),
    )
    actual_outline_segments.add(
        tuple(
            coordinate
            for point in points
            for coordinate in (
                round(pcbnew.ToMM(point.x), 3),
                round(pcbnew.ToMM(point.y), 3),
            )
        )
    )
if len(actual_outline_segments) != len(outline):
    fail("board outline segment count does not match approved geometry")
if actual_outline_segments != expected_outline_segments:
    fail("board rounded Edge.Cuts does not match approved plate outline")

# Board-level comments graphics were inherited from the Sofle reference and
# looked like copper touching the finished edge.  Footprint-local comments
# (for example, mounting-hole documentation) are still allowed.
comment_drawings = [
    drawing for drawing in board.GetDrawings()
    if drawing.GetLayerName() == "User.Comments"
]
if comment_drawings:
    fail(f"obsolete User.Comments board guides remain: {len(comment_drawings)}")

revision_mark = f"REV {layout['revision'].upper()} • REVERSIBLE LEFT / RIGHT"
if args.direct_rgb:
    revision_mark = revision_mark.replace("REV GAMMA", "GAMMA-D")
revision_layers = {
    drawing.GetLayerName()
    for drawing in board.GetDrawings()
    if isinstance(drawing, pcbnew.PCB_TEXT) and drawing.GetText() == revision_mark
}
if revision_layers != {"F.Silkscreen", "B.Silkscreen"}:
    fail(f"Rev {layout['revision']} reversible marking must appear on both silkscreen faces")

required_assembly_labels = [
    ("RIGHT HELIOS • F.Cu FACE", "F.Silkscreen", 120, 36.5),
    ("LEFT HELIOS • B.Cu FACE", "B.Silkscreen", 120, 36.5),
    ("R", "F.Silkscreen", 92.18, 38.9),
    ("R", "F.Silkscreen", 107.42, 38.9),
    ("L", "B.Silkscreen", 93.479, 40.1),
    ("L", "B.Silkscreen", 108.719, 40.1),
]
board_text = [
    drawing for drawing in board.GetDrawings()
    if isinstance(drawing, pcbnew.PCB_TEXT)
]
for label, layer, expected_x, expected_y in required_assembly_labels:
    if not any(
        drawing.GetText() == label
        and drawing.GetLayerName() == layer
        and close(pcbnew.ToMM(drawing.GetPosition().x), expected_x)
        and close(pcbnew.ToMM(drawing.GetPosition().y), expected_y)
        for drawing in board_text
    ):
        fail(f"missing local assembly label {label!r} on {layer}")
if any(
    "JP_HAND" in drawing.GetText()
    or drawing.GetText() in {"HAND", "L 1-2", "R 2-3"}
    for drawing in board_text
):
    fail("obsolete manual handedness instructions remain on the board")

for index in range(1, 7):
    hole = pad(footprints[f"H{index}"], "")
    if hole is None or hole.GetDrillSize().x != pcbnew.FromMM(2.2):
        fail(f"H{index}: expected 2.2 mm M2 clearance hole")

# Keep every plated component hole at or above the fabricator's recommended
# 0.25 mm annular ring.  This includes the EC11's two oval mechanical tabs;
# their former 3.2 x 2.0 mm pads left only 0.20 mm beside a 2.8 x 1.5 mm slot.
for footprint in board.GetFootprints():
    for item in footprint.Pads():
        if item.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
            continue
        drill = item.GetDrillSize()
        size = item.GetSize()
        annular_ring = min(size.x - drill.x, size.y - drill.y) / 2
        if annular_ring < pcbnew.FromMM(0.25):
            fail(
                f"{footprint.GetReference()} pad {item.GetNumber()}: "
                f"plated-hole annular ring is only "
                f"{pcbnew.ToMM(annular_ring):.3f} mm"
            )

# Use the larger profile by default. The compact profile is retained only for
# the dense reversible escape routing; enlarging those vias creates clearance
# violations. Both profiles remain comfortably within the target fab's rules.
allowed_vias = {(0.4, 0.2), (0.6, 0.3)}
for item in board.GetTracks():
    if type(item).__name__ == "PCB_TRACK":
        if item.GetStart() == item.GetEnd():
            fail(f"{item.GetNetname()}: zero-length copper segment remains")
        if item.GetWidth() < pcbnew.FromMM(0.20):
            fail(f"{item.GetNetname()}: track width is below 0.20 mm")
        continue
    if type(item).__name__ != "PCB_VIA":
        continue
    via_profile = (
        round(pcbnew.ToMM(item.GetWidth(pcbnew.F_Cu)), 3),
        round(pcbnew.ToMM(item.GetDrillValue()), 3),
    )
    if via_profile not in allowed_vias:
        fail(f"{item.GetNetname()}: unapproved via diameter/drill {via_profile}")
    if not item.IsTented(pcbnew.F_Cu) or not item.IsTented(pcbnew.B_Cu):
        fail(f"{item.GetNetname()}: untented via remains")

required_nets = {
    "VBUS", "VCC3V3", "GND", "RESET", "SPLIT_DATA", "HAND_L", "HAND_R",
    "OLED_SDA", "OLED_SCL", "RGB_MCU", "RGB_5V", "RGB_LED_IN",
    "ENC_A", "ENC_B", "KEY_ENC",
}
if args.direct_rgb:
    required_nets.discard("RGB_5V")
required_nets.update(f"ROW{i}" for i in range(5))
required_nets.update(f"COL{i}" for i in range(6))
missing_nets = sorted(name for name in required_nets if board.FindNet(name) is None)
if missing_nets:
    fail(f"missing nets: {', '.join(missing_nets)}")

expected_helios = {
    "1": "RGB_MCU", "2": "SPLIT_DATA", "3": "GND", "4": "GND",
    "5": "OLED_SDA", "6": "OLED_SCL",
    "8": "ROW0", "9": "ROW1", "10": "ROW2", "11": "ROW3",
    "12": "ROW4", "13": "COL5", "14": "COL4", "15": "COL3",
    "16": "COL2", "17": "COL1", "18": "COL0", "19": "ENC_B",
    "20": "ENC_A", "21": "VCC3V3", "22": "RESET", "23": "GND",
    "24": "VBUS",
}
for number, expected in expected_helios.items():
    if net(footprints["U1"], number) != expected:
        fail(f"U1 pad {number}: expected {expected}")

right_d4 = pad_on_layer(footprints["U1"], "7", pcbnew.F_SilkS)
left_d4 = pad_on_layer(footprints["U1"], "L7", pcbnew.B_SilkS)
if right_d4 is None or right_d4.GetNetname() != "HAND_R":
    fail("U1 R-position D4 must use isolated HAND_R")
if left_d4 is None or left_d4.GetNetname() != "HAND_L":
    fail("U1 L-position D4 must use isolated HAND_L")

# Keep the checked-in QMK definition tied to those same PCB nets and the
# ProMicro-compatible aliases used by QMK's Helios converter.
if keyboard.get("diode_direction") != "COL2ROW":
    fail("QMK diode direction must be COL2ROW")
if keyboard.get("matrix_pins") != {
    "rows": ["C6", "D7", "E6", "B4", "B5"],
    "cols": ["F6", "F7", "B1", "B3", "B2", "B6"],
}:
    fail("QMK matrix pins do not match U1 row/column nets")
split = keyboard.get("split", {})
if split.get("serial") != {"driver": "vendor", "pin": "D2"}:
    fail("QMK split serial must use controller D2 vendor transport")
if split.get("transport", {}).get("protocol") != "serial":
    fail("QMK split transport must be serial")
if split.get("handedness", {}).get("pin") != "D4":
    fail("QMK handedness pin must match the isolated U1 D4 header positions")
if keyboard.get("ws2812", {}).get("pin") != "D3":
    fail("QMK WS2812 pin must match U1 RGB_MCU on D3")
if keyboard.get("rgb_matrix", {}).get("split_count") != [28, 28]:
    fail("QMK RGB matrix must contain 28 LEDs per half")
for feature in ("encoder", "oled", "rgb_matrix"):
    if keyboard.get("features", {}).get(feature) is not True:
        fail(f"QMK feature {feature} must be enabled")
if keyboard.get("encoder", {}).get("rotary") != [
    {"pin_a": "F4", "pin_b": "F5", "resolution": 2}
]:
    fail("QMK left encoder pins do not match U1 ENC_A/ENC_B")
if split.get("encoder", {}).get("right", {}).get("rotary") != [
    {"pin_a": "F5", "pin_b": "F4", "resolution": 2}
]:
    fail("QMK right encoder pins must reverse for the mirrored assembly")
config_h = (FIRMWARE / "config.h").read_text()
if "#define I2C1_SDA_PIN D1" not in config_h or "#define I2C1_SCL_PIN D0" not in config_h:
    fail("QMK OLED I2C pins do not match U1 OLED_SDA/OLED_SCL")
if "SPLIT_HAND_PIN_LOW_IS_LEFT" in config_h:
    fail("QMK handedness polarity must remain high=left and low=right")
if "CONVERT_TO = elite_pi" not in (FIRMWARE / "rules.mk").read_text():
    fail("QMK build must target the Keebio Elite-Pi converter")

if args.direct_rgb:
    if net(footprints["R1"], "1") != "RGB_MCU" or net(footprints["R1"], "2") != "RGB_LED_IN":
        fail("direct RGB must route GPIO through R1 to LED DIN")
    if footprints["R1"].GetValue() != "330R":
        fail("direct RGB R1 must retain the nominal 330 ohm series resistor")
else:
    expected_buffer = {"1": "GND", "2": "RGB_MCU", "3": "GND", "4": "RGB_5V", "5": "VBUS"}
    for number, expected in expected_buffer.items():
        if net(footprints["U2"], number) != expected:
            fail(f"U2 pad {number}: expected {expected}")

expected_trrs = {"S": "GND", "R2": "VBUS", "R1": "TRRS_SPARE", "T": "SPLIT_DATA"}
for number, expected in expected_trrs.items():
    if net(footprints["J1"], number) != expected:
        fail(f"J1 pad {number}: expected {expected}")
trrs = layout["trrs"]
trrs_x, trrs_y = position_mm(footprints["J1"])
trrs_rotation = footprints["J1"].GetOrientationDegrees() % 360
if not (
    close(trrs_x, trrs["pcbCenter"]["x"])
    and close(trrs_y, trrs["pcbCenter"]["y"])
    and close(trrs_rotation, trrs["pcbRotation"])
):
    fail(
        f"J1 must face the inner edge at {trrs['pcbCenter']['x']:.3f},"
        f"{trrs['pcbCenter']['y']:.3f} @ {trrs['pcbRotation']:.1f} degrees"
    )

if footprints["R4"].GetValue() != "10k" or [net(footprints["R4"], number) for number in ("1", "2")] != ["HAND_L", "VCC3V3"]:
    fail("R4 must pull the L-position D4 high through 10k")
if footprints["R5"].GetValue() != "10k" or [net(footprints["R5"], number) for number in ("1", "2")] != ["HAND_R", "GND"]:
    fail("R5 must pull the R-position D4 low through 10k")
expected_test_points = {
    "TP1": "GND",
    "TP2": "VBUS",
    "TP3": "VCC3V3",
    "TP4": "SPLIT_DATA",
    "TP6": "RGB_LED_IN",
    "TP7": "OLED_SDA",
    "TP8": "OLED_SCL",
}
for reference, expected in expected_test_points.items():
    if net(footprints[reference], "1") != expected:
        fail(f"{reference}: expected {expected} test point")

for switch_number in KEY_SWITCHES:
    switch = footprints[f"SW{switch_number}"]
    diode = footprints[f"D{switch_number}"]
    if net(switch, "1") != "VBUS" or net(switch, "3") != "GND":
        fail(f"SW{switch_number}: RGB power pads are wrong")
    if net(switch, "5") != net(diode, "2"):
        fail(f"SW{switch_number}: switch-to-diode net is broken")
    if not net(diode, "1").startswith("ROW"):
        fail(f"D{switch_number}: cathode pad 1 must connect to a row")
    if not net(switch, "6").startswith("COL"):
        fail(f"SW{switch_number}: matrix pad must connect to a column")

# Rev Gamma moves the four thumb diodes from the irregular Rev Beta offsets
# to reviewed, solderable positions behind their sockets.  D27 stays another
# millimetre out to clear COL4, while D29 gets the largest gap and flips 180
# degrees so its two routed nets do not cross on either reversible face.
thumb_diode = layout["thumbArc"]["diodePlacement"]
if thumb_diode["nominalSocketBodyGap"] < 1.5:
    fail("thumb-diode nominal socket-body gap must remain at least 1.5 mm")
for switch_number in range(26, 30):
    switch = footprints[f"SW{switch_number}"]
    diode = footprints[f"D{switch_number}"]
    switch_x, switch_y = position_mm(switch)
    local_x = thumb_diode["localOffsetX"]
    local_y = thumb_diode.get("perSwitchLocalOffsetY", {}).get(
        str(switch_number), thumb_diode["localOffsetY"]
    )
    angle = math.radians(-switch.GetOrientationDegrees())
    expected_x = switch_x + local_x * math.cos(angle) - local_y * math.sin(angle)
    expected_y = switch_y + local_x * math.sin(angle) + local_y * math.cos(angle)
    actual_x, actual_y = position_mm(diode)
    if not close(actual_x, expected_x, 0.002) or not close(actual_y, expected_y, 0.002):
        fail(
            f"D{switch_number}: Gamma placement {actual_x:.3f},{actual_y:.3f} "
            f"does not match {expected_x:.3f},{expected_y:.3f}"
        )
    orientation_delta = thumb_diode.get("perSwitchOrientationDelta", {}).get(
        str(switch_number), 0
    )
    expected_orientation = (
        switch.GetOrientationDegrees() + orientation_delta
    ) % 360
    actual_orientation = diode.GetOrientationDegrees() % 360
    if abs((actual_orientation - expected_orientation + 180) % 360 - 180) > 0.01:
        fail(
            f"D{switch_number}: Gamma orientation {actual_orientation:.1f} "
            f"does not match {expected_orientation:.1f}"
        )

# Follow data by net name rather than reference order; Sofle snakes its RGB
# path through columns and the Arc thumb cluster.
remaining = set(KEY_SWITCHES)
current_net = "RGB_LED_IN"
led_chain = []
while remaining:
    matches = [
        number for number in remaining
        if net(footprints[f"SW{number}"], "4") == current_net
    ]
    if len(matches) != 1:
        fail(
            f"RGB chain must have one next LED after {current_net}; "
            f"found {matches or 'none'}"
        )
    switch_number = matches[0]
    remaining.remove(switch_number)
    led_chain.append(switch_number)
    current_net = net(footprints[f"SW{switch_number}"], "2")
if len(led_chain) != 28:
    fail(f"expected one 28-LED chain, found {len(led_chain)} LEDs")

encoder = footprints["SW25"]
if {net(encoder, "A"), net(encoder, "B"), net(encoder, "C")} != {"ENC_A", "ENC_B", "GND"}:
    fail("SW25: encoder rotation pins are wrong")
if net(encoder, "S1") != "COL5" or net(encoder, "S2") != "KEY_ENC":
    fail("SW25: encoder switch nets are wrong")
if net(footprints["D25"], "1") != "ROW4" or net(footprints["D25"], "2") != "KEY_ENC":
    fail("D25: encoder switch diode is wrong")

# Keep the SW19-to-SW26 reversible contact route inside the rounded thumb
# sweep. The former route continued vertically to y=162.864 mm and looked
# like a blue tail leaving the intended enclosure. The exact layer-change
# topology is intentionally not pinned because the RGB-aperture reroute uses
# a different, DRC-clean path.
switch_route = [
    track for track in board.GetTracks()
    if track.GetNetname() == "Net-(SW19-Pad2)"
]
if any(
    track.GetLayer() == pcbnew.B_Cu
    and close(pcbnew.ToMM(track.GetStart().x), 118.063)
    and close(pcbnew.ToMM(track.GetEnd().x), 118.063)
    and max(
        pcbnew.ToMM(track.GetStart().y),
        pcbnew.ToMM(track.GetEnd().y),
    ) > 150.001
    for track in switch_route
):
    fail("SW19-to-SW26 B.Cu route extends below the approved thumb sweep")

# The old VBUS route below the encoder ran left to an unconnected waypoint and
# immediately doubled back.  It added copper length and a visible U-turn but no
# connectivity, so keep that legacy waypoint out of the canonical board.
legacy_vbus_u_turn = (91.581931, 118.5)
if any(
    track.GetNetname() == "VBUS"
    and track.GetLayer() == pcbnew.F_Cu
    and any(
        close(pcbnew.ToMM(endpoint.x), legacy_vbus_u_turn[0])
        and close(pcbnew.ToMM(endpoint.y), legacy_vbus_u_turn[1])
        for endpoint in (track.GetStart(), track.GetEnd())
    )
    for track in board.GetTracks()
):
    fail("legacy VBUS U-turn remains below the encoder")

# Pin the two other pad-free route overshoots found by the whole-board copper
# topology audit.  Intentional reversible-pad escapes make short local jogs,
# but neither of these old turnaround points had a pad, via, or branch.
legacy_route_turnarounds = {
    ("COL4", pcbnew.B_Cu): (138.625, 114.275),
    ("Net-(SW20-Pad4)", pcbnew.B_Cu): (136.6, 112.8),
    ("COL3", pcbnew.B_Cu): (84.0, 122.6),
    ("ENC_A", pcbnew.B_Cu): (109.0, 109.65),
}
for (net_name, layer), turnaround in legacy_route_turnarounds.items():
    if any(
        track.GetNetname() == net_name
        and track.GetLayer() == layer
        and any(
            close(pcbnew.ToMM(endpoint.x), turnaround[0])
            and close(pcbnew.ToMM(endpoint.y), turnaround[1])
            for endpoint in (track.GetStart(), track.GetEnd())
        )
        for track in board.GetTracks()
    ):
        fail(f"legacy {net_name} route turnaround remains at {turnaround}")

# The SW26 COL4 route already reaches its layer-change via through the inward
# branch. This endpoint belonged to a second branch that looped toward the
# board edge and touched same-net copper without serving a pad or via.
legacy_col4_tail_endpoint = (80.720728, 170.104978)
if any(
    track.GetNetname() == "COL4"
    and track.GetLayer() == pcbnew.B_Cu
    and any(
        close(pcbnew.ToMM(endpoint.x), legacy_col4_tail_endpoint[0])
        and close(pcbnew.ToMM(endpoint.y), legacy_col4_tail_endpoint[1])
        for endpoint in (track.GetStart(), track.GetEnd())
    )
    for track in board.GetTracks()
):
    fail("legacy redundant COL4 tail remains beside SW26")

# Keep the COL3 run beside the thumb cluster as a simple right-angle route.
# The former five-piece kink stepped left and then doubled back to the same
# horizontal run without clearing any copper, pad, via, or board feature.
legacy_col3_corner_points = {
    (86.0, 131.6),
    (85.672577, 132.64773),
    (85.672577, 135.04773),
    (86.75, 134.5),
}
if any(
    track.GetNetname() == "COL3"
    and track.GetLayer() == pcbnew.B_Cu
    and any(
        any(
            close(pcbnew.ToMM(endpoint.x), point[0])
            and close(pcbnew.ToMM(endpoint.y), point[1])
            for point in legacy_col3_corner_points
        )
        for endpoint in (track.GetStart(), track.GetEnd())
    )
    for track in board.GetTracks()
):
    fail("legacy COL3 kink remains beside the thumb cluster")
expected_col3_corner_segments = {
    tuple(sorted(((86.0, 124.6), (86.0, 134.5)))),
    tuple(sorted(((86.0, 134.5), (93.0, 134.5)))),
}
actual_col3_corner_segments = {
    tuple(
        sorted(
            (
                (round(pcbnew.ToMM(track.GetStart().x), 6), round(pcbnew.ToMM(track.GetStart().y), 6)),
                (round(pcbnew.ToMM(track.GetEnd().x), 6), round(pcbnew.ToMM(track.GetEnd().y), 6)),
            )
        )
    )
    for track in board.GetTracks()
    if track.GetNetname() == "COL3" and track.GetLayer() == pcbnew.B_Cu
}
if not expected_col3_corner_segments.issubset(actual_col3_corner_segments):
    fail("simple COL3 right-angle route is missing beside the thumb cluster")

# Prevent the dense legacy stair-step polylines from returning. This region
# includes the four thumb switches and their routes back toward the matrix.
thumb_tracks = []
duplicate_tracks = set()
seen_tracks = set()
for track in board.GetTracks():
    if type(track).__name__ != "PCB_TRACK":
        continue
    start = track.GetStart()
    end = track.GetEnd()
    start_point = (start.x, start.y)
    end_point = (end.x, end.y)
    if start_point != end_point:
        identity = (
            track.GetNetCode(),
            track.GetLayer(),
            track.GetWidth(),
            min(start_point, end_point),
            max(start_point, end_point),
        )
        if identity in seen_tracks:
            duplicate_tracks.add(identity)
        seen_tracks.add(identity)
    midpoint_x = pcbnew.ToMM(start.x + end.x) / 2
    midpoint_y = pcbnew.ToMM(start.y + end.y) / 2
    if 65 <= midpoint_x <= 150 and 110 <= midpoint_y <= 180:
        thumb_tracks.append(track)
if duplicate_tracks:
    fail(f"{len(duplicate_tracks)} duplicate non-zero copper segments remain")
if len(thumb_tracks) > 500:
    fail(f"thumb routing regressed to {len(thumb_tracks)} fragmented segments")
board.BuildConnectivity()
unconnected = board.GetConnectivity().GetUnconnectedCount(False)
if unconnected:
    fail(f"{unconnected} unrouted connections remain")
if not list(board.GetTracks()):
    fail("no routed copper present")

print(
    f"PASS: {BOARD.name} — {len(footprints)} footprints, "
    f"{len(list(board.GetTracks()))} copper items, 28-key RGB chain, "
    f"rounded Rev {layout['revision']} geometry and controller QMK mapping matched, "
    "matrix/controller/OLED/TRRS "
    "nets present, zero unrouted connections"
)
