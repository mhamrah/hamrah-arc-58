#!/usr/bin/env python3
"""Apply the reviewed Rev Gamma thumb-diode placement to the KiCad PCB.

The four thumb switches keep their existing centers and rotations.  Each
SOD-123 diode is centered 10.5 mm behind its switch and aligned with the
switch tangent.  Moving the first attached track endpoint with the footprint
preserves the reviewed route outside the component placement area.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOARD = ROOT / "hardware" / "kicad" / "arc58-reversible.kicad_pcb"
CONFIG = json.loads((ROOT / "layout.config.json").read_text())
POSITION_TOLERANCE_NM = 10
ANGLE_TOLERANCE_DEG = 0.001


@dataclass(frozen=True)
class RemovedConnection:
    pad_number: str
    other_end: pcbnew.VECTOR2I
    width: int
    layer: int
    net_code: int


def close(first: pcbnew.VECTOR2I, second: pcbnew.VECTOR2I) -> bool:
    return (
        abs(first.x - second.x) <= POSITION_TOLERANCE_NM
        and abs(first.y - second.y) <= POSITION_TOLERANCE_NM
    )


def normalized_angle_difference(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0)


def target_position(switch: pcbnew.FOOTPRINT) -> pcbnew.VECTOR2I:
    placement = CONFIG["thumbArc"]["diodePlacement"]
    switch_number = switch.GetReference().removeprefix("SW")
    local_y = placement.get("perSwitchLocalOffsetY", {}).get(
        switch_number, placement["localOffsetY"]
    )
    return transformed_position(
        switch,
        placement["localOffsetX"],
        local_y,
    )


def transformed_position(
    switch: pcbnew.FOOTPRINT,
    local_x: float,
    local_y: float,
) -> pcbnew.VECTOR2I:

    # pcbnew reports the clockwise footprint rotation; ordinary Cartesian
    # rotation therefore uses the opposite sign.
    angle = math.radians(-switch.GetOrientation().AsDegrees())
    global_x = local_x * math.cos(angle) - local_y * math.sin(angle)
    global_y = local_x * math.sin(angle) + local_y * math.cos(angle)
    switch_position = switch.GetPosition()
    return pcbnew.VECTOR2I(
        switch_position.x + int(round(global_x * 1_000_000)),
        switch_position.y + int(round(global_y * 1_000_000)),
    )


def pad_on_layer(
    footprint: pcbnew.FOOTPRINT,
    number: str,
    layer: int,
) -> pcbnew.PAD:
    matches = [
        pad
        for pad in footprint.Pads()
        if pad.GetNumber() == number and pad.GetLayerSet().Contains(layer)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one {footprint.GetReference()} pad {number} on "
            f"{pcbnew.LayerName(layer)}, found {len(matches)}"
        )
    return matches[0]


def add_track(
    board: pcbnew.BOARD,
    start: pcbnew.VECTOR2I,
    end: pcbnew.VECTOR2I,
    layer: int,
    net_code: int,
    width_mm: float = 0.25,
) -> None:
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(start)
    track.SetEnd(end)
    track.SetWidth(pcbnew.FromMM(width_mm))
    track.SetLayer(layer)
    track.SetNetCode(net_code)
    board.Add(track)


def add_via(
    board: pcbnew.BOARD,
    position: pcbnew.VECTOR2I,
    net_code: int,
) -> None:
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(position)
    via.SetWidth(pcbnew.FromMM(0.4))
    via.SetDrill(pcbnew.FromMM(0.2))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNetCode(net_code)
    board.Add(via)


def rebuild_thumb_routes(
    board: pcbnew.BOARD,
    footprints: dict[str, pcbnew.FOOTPRINT],
) -> None:
    """Build short socket routes and a clean shared ROW4 arc."""
    row_net_code = board.FindNet("ROW4").GetNetCode()
    all_copper_items = list(board.GetTracks())
    socket_routes = []
    row_pad_positions = []
    diode_vias: dict[int, pcbnew.VECTOR2I] = {}
    for number in range(26, 30):
        diode = footprints[f"D{number}"]
        switch = footprints[f"SW{number}"]
        placement = CONFIG["thumbArc"]["diodePlacement"]
        diode_offset_y = placement.get("perSwitchLocalOffsetY", {}).get(
            str(number), placement["localOffsetY"]
        )
        row_pad_1 = pad_on_layer(diode, "1", pcbnew.F_Cu).GetPosition()
        row_pad_2 = pad_on_layer(diode, "2", pcbnew.F_Cu).GetPosition()
        tangent_x = row_pad_1.x - row_pad_2.x
        tangent_y = row_pad_1.y - row_pad_2.y
        tangent_length = math.hypot(tangent_x, tangent_y)
        row_via_extension = 1.0 if number == 29 else 1.5
        diode_vias[number] = pcbnew.VECTOR2I(
            row_pad_1.x
            + int(round(tangent_x / tangent_length * pcbnew.FromMM(row_via_extension))),
            row_pad_1.y
            + int(round(tangent_y / tangent_length * pcbnew.FromMM(row_via_extension))),
        )
        switch_position = switch.GetPosition()
        diode_position = diode.GetPosition()
        radial_x = diode_position.x - switch_position.x
        radial_y = diode_position.y - switch_position.y
        radial_length = math.hypot(radial_x, radial_y)
        unique_via_distance = 0.5 if number == 29 else 1.5
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            diode_pad_2 = pad_on_layer(diode, "2", layer)
            socket_pad = pad_on_layer(switch, "5", layer)
            socket_routes.append(
                (
                    number,
                    diode_pad_2.GetPosition(),
                    socket_pad.GetPosition(),
                    layer,
                    diode_pad_2.GetNetCode(),
                    pcbnew.VECTOR2I(
                        diode_pad_2.GetPosition().x
                        + int(round(radial_x / radial_length * pcbnew.FromMM(unique_via_distance))),
                        diode_pad_2.GetPosition().y
                        + int(round(radial_y / radial_length * pcbnew.FromMM(unique_via_distance))),
                    ),
                )
            )
            row_pad_positions.append(
                (layer, pad_on_layer(diode, "1", layer).GetPosition(), diode_vias[number])
            )

    diode_net_names = {f"Net-(D{number}-Pad2)" for number in range(26, 30)}
    for item in all_copper_items:
        if item.GetNetname() in diode_net_names:
            board.Remove(item)

    unique_vias = {}
    bridge_vias = set()
    bridge_positions = {}
    for number, start, end, layer, net_code, via_position in socket_routes:
        if number not in unique_vias:
            add_via(board, via_position, net_code)
            unique_vias[number] = via_position
        add_track(board, start, via_position, layer, net_code)
        blocked_layer = (
            (number in (26, 27) and layer == pcbnew.F_Cu)
            or (number == 29 and layer == pcbnew.B_Cu)
        )
        if blocked_layer:
            toward_diode_x = start.x - end.x
            toward_diode_y = start.y - end.y
            toward_diode_length = math.hypot(toward_diode_x, toward_diode_y)
            bridge_position = pcbnew.VECTOR2I(
                end.x
                + int(round(toward_diode_x / toward_diode_length * pcbnew.FromMM(1.0))),
                end.y
                + int(round(toward_diode_y / toward_diode_length * pcbnew.FromMM(1.0))),
            )
            if number not in bridge_vias:
                add_via(board, bridge_position, net_code)
                bridge_vias.add(number)
                bridge_positions[number] = bridge_position
            add_track(board, end, bridge_position, layer, net_code)
            bridge_layer = pcbnew.B_Cu if layer == pcbnew.F_Cu else pcbnew.F_Cu
            if number == 27:
                bridge_points = [
                    via_position,
                    pcbnew.VECTOR2I(pcbnew.FromMM(102.0), pcbnew.FromMM(157.0)),
                    pcbnew.VECTOR2I(pcbnew.FromMM(95.0), pcbnew.FromMM(157.0)),
                    pcbnew.VECTOR2I(pcbnew.FromMM(94.75), pcbnew.FromMM(156.0)),
                    pcbnew.VECTOR2I(pcbnew.FromMM(94.75), bridge_position.y),
                    bridge_position,
                ]
                for bridge_start, bridge_end in zip(
                    bridge_points, bridge_points[1:]
                ):
                    add_track(
                        board,
                        bridge_start,
                        bridge_end,
                        pcbnew.F_Cu,
                        net_code,
                    )
            else:
                add_track(
                    board,
                    via_position,
                    bridge_position,
                    bridge_layer,
                    net_code,
                )
            points = []
        elif layer == pcbnew.B_Cu and number == 27:
            points = [
                bridge_positions[27],
                pcbnew.VECTOR2I(pcbnew.FromMM(100.75), pcbnew.FromMM(151.25)),
                pcbnew.VECTOR2I(pcbnew.FromMM(100.75), end.y),
                end,
            ]
        else:
            points = [via_position, end]
        for route_start, route_end in zip(points, points[1:]):
            add_track(board, route_start, route_end, layer, net_code)

    thumb_route_start_y = pcbnew.FromMM(120.21)
    for item in all_copper_items:
        if item.GetNetCode() != row_net_code:
            continue
        if type(item).__name__ == "PCB_VIA":
            if item.GetPosition().y > pcbnew.FromMM(130.0):
                board.Remove(item)
        elif type(item).__name__ == "PCB_TRACK" and max(
            item.GetStart().y, item.GetEnd().y
        ) > thumb_route_start_y:
            board.Remove(item)

    for via_position in diode_vias.values():
        add_via(board, via_position, row_net_code)
    for layer, pad_position, via_position in row_pad_positions:
        add_track(
            board,
            pad_position,
            via_position,
            layer,
            row_net_code,
        )

    # Continue the existing controller-side ROW4 route to the outer side of
    # D28, then follow the thumb fan through all four local vias.
    anchor = pcbnew.VECTOR2I(
        pcbnew.FromMM(112.879188), pcbnew.FromMM(120.206293)
    )
    entry = [
        anchor,
        pcbnew.VECTOR2I(pcbnew.FromMM(118.816388), pcbnew.FromMM(126.143493)),
        pcbnew.VECTOR2I(pcbnew.FromMM(118.816388), pcbnew.FromMM(137.952693)),
        diode_vias[28],
    ]
    for start, end in zip(entry, entry[1:]):
        add_track(board, start, end, pcbnew.B_Cu, row_net_code)
    row_chains = [
        (
            pcbnew.B_Cu,
            [
                diode_vias[26],
                pcbnew.VECTOR2I(pcbnew.FromMM(96.0), pcbnew.FromMM(158.0)),
                pcbnew.VECTOR2I(pcbnew.FromMM(105.5), pcbnew.FromMM(158.0)),
                pcbnew.VECTOR2I(pcbnew.FromMM(105.5), pcbnew.FromMM(152.0)),
                diode_vias[27],
            ],
        ),
        (
            pcbnew.B_Cu,
            [
                diode_vias[27],
                pcbnew.VECTOR2I(pcbnew.FromMM(108.0), pcbnew.FromMM(147.0)),
                pcbnew.VECTOR2I(pcbnew.FromMM(120.0), pcbnew.FromMM(147.0)),
                pcbnew.VECTOR2I(pcbnew.FromMM(120.0), pcbnew.FromMM(141.0)),
                diode_vias[28],
            ],
        ),
        (pcbnew.F_Cu, [diode_vias[28], diode_vias[29]]),
    ]
    for layer, points in row_chains:
        for start, end in zip(points, points[1:]):
            add_track(board, start, end, layer, row_net_code)


def unique_pad_positions(footprint: pcbnew.FOOTPRINT) -> dict[str, pcbnew.VECTOR2I]:
    positions: dict[str, pcbnew.VECTOR2I] = {}
    for pad in footprint.Pads():
        positions.setdefault(pad.GetNumber(), pad.GetPosition())
    return positions


def detach_tracks(
    board: pcbnew.BOARD,
    footprint: pcbnew.FOOTPRINT,
) -> list[RemovedConnection]:
    positions = unique_pad_positions(footprint)
    pad_nets = {
        pad.GetNumber(): pad.GetNetCode()
        for pad in footprint.Pads()
    }
    removed: list[RemovedConnection] = []
    for track in list(board.GetTracks()):
        if type(track).__name__ != "PCB_TRACK":
            continue
        for pad_number, pad_position in positions.items():
            if track.GetNetCode() != pad_nets[pad_number]:
                continue
            if close(track.GetStart(), pad_position):
                other_end = track.GetEnd()
            elif close(track.GetEnd(), pad_position):
                other_end = track.GetStart()
            else:
                continue
            removed.append(
                RemovedConnection(
                    pad_number=pad_number,
                    other_end=pcbnew.VECTOR2I(other_end.x, other_end.y),
                    width=track.GetWidth(),
                    layer=track.GetLayer(),
                    net_code=track.GetNetCode(),
                )
            )
            board.Remove(track)
            break
    return removed


def reconnect_tracks(
    board: pcbnew.BOARD,
    footprint: pcbnew.FOOTPRINT,
    connections: list[RemovedConnection],
) -> None:
    positions = unique_pad_positions(footprint)
    for connection in connections:
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(positions[connection.pad_number])
        track.SetEnd(connection.other_end)
        track.SetWidth(connection.width)
        track.SetLayer(connection.layer)
        track.SetNetCode(connection.net_code)
        board.Add(track)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--output", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    board = pcbnew.LoadBoard(str(args.input))
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    changes = []
    for number in range(26, 30):
        switch = footprints[f"SW{number}"]
        diode = footprints[f"D{number}"]
        position = target_position(switch)
        placement = CONFIG["thumbArc"]["diodePlacement"]
        orientation_delta = placement.get("perSwitchOrientationDelta", {}).get(
            str(number), 0
        )
        orientation = switch.GetOrientation().AsDegrees() + orientation_delta
        current_orientation = diode.GetOrientation().AsDegrees()
        if close(position, diode.GetPosition()) and normalized_angle_difference(
            orientation, current_orientation
        ) <= ANGLE_TOLERANCE_DEG:
            continue

        connections = detach_tracks(board, diode)
        diode.SetPosition(position)
        diode.SetOrientation(pcbnew.EDA_ANGLE(orientation, pcbnew.DEGREES_T))
        reconnect_tracks(board, diode, connections)
        changes.append(
            f"D{number}=({pcbnew.ToMM(position.x):.3f}, "
            f"{pcbnew.ToMM(position.y):.3f}) @ {orientation:.1f}°; "
            f"{len(connections)} track endpoints moved"
        )

    revision_mark = f"REV {CONFIG['revision'].upper()} • REVERSIBLE LEFT / RIGHT"
    for drawing in board.GetDrawings():
        if isinstance(drawing, pcbnew.PCB_TEXT) and "REVERSIBLE LEFT / RIGHT" in drawing.GetText():
            drawing.SetText(revision_mark)

    rebuild_thumb_routes(board, footprints)

    pcbnew.SaveBoard(str(args.output), board)
    if changes:
        print("Rev Gamma thumb-diode placement applied:")
        for change in changes:
            print(f"- {change}")
    else:
        print("Rev Gamma thumb-diode placement already applied; routes rebuilt")


if __name__ == "__main__":
    main()
