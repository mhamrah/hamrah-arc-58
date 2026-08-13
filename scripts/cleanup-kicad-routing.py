#!/usr/bin/env python3
"""Simplify legacy thumb-route polylines without changing their connectivity."""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOARD = ROOT / "hardware" / "kicad" / "arc58-reversible.kicad_pcb"
THUMB_BOUNDS = (65.0, 150.0, 110.0, 180.0)
DEFAULT_TOLERANCE_MM = 0.20

# These routes pass close to existing pads, holes, or vias. Smaller tolerances
# retain their reviewed clearance while still collapsing collinear fragments.
TOLERANCE_LIMITS_MM = {
    ("COL5", pcbnew.B_Cu): 0.05,
    ("Net-(SW20-Pad4)", pcbnew.B_Cu): 0.05,
    ("GND", pcbnew.F_Cu): 0.10,
    ("COL4", pcbnew.B_Cu): 0.10,
    ("VBUS", pcbnew.F_Cu): 0.15,
    ("COL1", pcbnew.F_Cu): 0.15,
}


def point(position: pcbnew.VECTOR2I) -> tuple[int, int]:
    return position.x, position.y


def distance_to_line(
    candidate: tuple[int, int],
    start: tuple[int, int],
    end: tuple[int, int],
) -> float:
    px, py = candidate
    ax, ay = start
    zx, zy = end
    dx, dy = zx - ax, zy - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    return abs(dx * (ay - py) - (ax - px) * dy) / math.hypot(dx, dy)


def simplify_polyline(
    points: list[tuple[int, int]], tolerance: int
) -> list[tuple[int, int]]:
    if len(points) <= 2:
        return points
    start, end = points[0], points[-1]
    distances = [distance_to_line(candidate, start, end) for candidate in points[1:-1]]
    maximum = max(distances, default=0.0)
    if maximum <= tolerance:
        return [start, end]
    split = distances.index(maximum) + 1
    return (
        simplify_polyline(points[: split + 1], tolerance)[:-1]
        + simplify_polyline(points[split:], tolerance)
    )


def touches_thumb_region(points: list[tuple[int, int]]) -> bool:
    x_min, x_max, y_min, y_max = THUMB_BOUNDS
    return any(
        x_min <= pcbnew.ToMM(x) <= x_max and y_min <= pcbnew.ToMM(y) <= y_max
        for x, y in points
    )


def add_track(
    board: pcbnew.BOARD,
    start: tuple[int, int],
    end: tuple[int, int],
    width: int,
    layer: int,
    net_code: int,
) -> pcbnew.PCB_TRACK:
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pcbnew.VECTOR2I(*start))
    track.SetEnd(pcbnew.VECTOR2I(*end))
    track.SetWidth(width)
    track.SetLayer(layer)
    track.SetNetCode(net_code)
    board.Add(track)
    return track


def replace_exact_chain(
    board: pcbnew.BOARD,
    tracks: list[pcbnew.PCB_TRACK],
    net_name: str,
    layer: int,
    points_mm: list[tuple[float, float]],
) -> int:
    """Replace one exact, unbranched detour with its direct connection."""
    # Round explicitly to KiCad's integer-nanometre grid. pcbnew.FromMM()
    # truncates a few six-decimal float literals one nanometre early.
    to_internal = lambda coordinates: tuple(
        int(round(value * 1_000_000)) for value in coordinates
    )
    points = [to_internal(coordinates) for coordinates in points_mm]
    entry, exit_point = points[0], points[-1]
    old_geometry = {
        (min(start, end), max(start, end))
        for start, end in zip(points, points[1:])
    }
    old_tracks = [
        track for track in tracks
        if track.GetNetname() == net_name
        and track.GetLayer() == layer
        and (
            min(point(track.GetStart()), point(track.GetEnd())),
            max(point(track.GetStart()), point(track.GetEnd())),
        ) in old_geometry
    ]
    if old_tracks and len(old_tracks) != len(old_geometry):
        raise RuntimeError(f"only part of the {net_name} detour was found")
    if not old_tracks:
        return 0
    widths = {track.GetWidth() for track in old_tracks}
    net_codes = {track.GetNetCode() for track in old_tracks}
    if len(widths) != 1 or len(net_codes) != 1:
        raise RuntimeError(f"{net_name} U-turn segments do not share one route style")
    for track in old_tracks:
        board.Remove(track)
        tracks.remove(track)
    tracks.append(
        add_track(
            board,
            entry,
            exit_point,
            widths.pop(),
            layer,
            net_codes.pop(),
        )
    )
    return len(old_tracks)


def replace_exact_u_turn(
    board: pcbnew.BOARD,
    tracks: list[pcbnew.PCB_TRACK],
    net_name: str,
    layer: int,
    entry_mm: tuple[float, float],
    turnaround_mm: tuple[float, float],
    exit_mm: tuple[float, float],
) -> int:
    return replace_exact_chain(
        board,
        tracks,
        net_name,
        layer,
        [entry_mm, turnaround_mm, exit_mm],
    )


def simplify_routes(
    board: pcbnew.BOARD, tolerance_mm: float
) -> tuple[int, int, int, int, int, int, int, int, int, int]:
    all_items = list(board.GetTracks())
    tracks = [item for item in all_items if type(item).__name__ == "PCB_TRACK"]
    vias = [item for item in all_items if type(item).__name__ == "PCB_VIA"]
    legacy_silkscreen = []
    for drawing in board.GetDrawings():
        if (
            type(drawing).__name__ != "PCB_SHAPE"
            or drawing.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS)
            or drawing.GetShapeStr() != "Line"
        ):
            continue
        start, end = drawing.GetStart(), drawing.GetEnd()
        length_mm = math.hypot(
            pcbnew.ToMM(end.x - start.x),
            pcbnew.ToMM(end.y - start.y),
        )
        dimensions = round(length_mm, 3), round(pcbnew.ToMM(drawing.GetWidth()), 3)
        if dimensions in {(1.0, 0.22), (1.4, 0.18)}:
            legacy_silkscreen.append(drawing)

    rgb_net_name = "Net-(SW19-Pad2)"
    rgb_net_code = board.FindNet(rgb_net_name).GetNetCode()
    rgb_route_points = [
        (pcbnew.FromMM(119.493), pcbnew.FromMM(120.917)),
        (pcbnew.FromMM(103.75), pcbnew.FromMM(123.5)),
        (pcbnew.FromMM(84.0), pcbnew.FromMM(143.25)),
        (pcbnew.FromMM(84.0), pcbnew.FromMM(148.5)),
    ]
    rgb_route_geometry = {
        (min(start, end), max(start, end))
        for start, end in zip(rgb_route_points, rgb_route_points[1:])
    }
    rgb_backtrack = []
    for track in tracks:
        if track.GetNetname() != rgb_net_name or track.GetLayer() != pcbnew.F_Cu:
            continue
        start, end = point(track.GetStart()), point(track.GetEnd())
        xs = pcbnew.ToMM(start[0]), pcbnew.ToMM(end[0])
        ys = pcbnew.ToMM(start[1]), pcbnew.ToMM(end[1])
        if min(xs) >= 83.9 and max(xs) <= 119.6 and min(ys) >= 120.8 and max(ys) <= 148.6:
            rgb_backtrack.append(track)
    existing_rgb_geometry = {
        (min(point(track.GetStart()), point(track.GetEnd())),
         max(point(track.GetStart()), point(track.GetEnd())))
        for track in rgb_backtrack
    }
    rgb_already_clean = existing_rgb_geometry == rgb_route_geometry

    # Remove a legacy VBUS U-turn below the encoder.  Nothing connects at the
    # leftmost point: the route travels 6.6 mm away from its destination and
    # immediately doubles back on the same layer.
    vbus_u_turn = (pcbnew.FromMM(91.581931), pcbnew.FromMM(118.5))
    vbus_entry = (pcbnew.FromMM(98.186219), pcbnew.FromMM(118.706293))
    vbus_exit = (pcbnew.FromMM(98.9499), pcbnew.FromMM(118.5))
    vbus_loop_geometry = {
        (min(vbus_entry, vbus_u_turn), max(vbus_entry, vbus_u_turn)),
        (min(vbus_u_turn, vbus_exit), max(vbus_u_turn, vbus_exit)),
    }
    vbus_loop = [
        track for track in tracks
        if track.GetNetname() == "VBUS"
        and track.GetLayer() == pcbnew.F_Cu
        and (
            min(point(track.GetStart()), point(track.GetEnd())),
            max(point(track.GetStart()), point(track.GetEnd())),
        ) in vbus_loop_geometry
    ]
    if vbus_loop and len(vbus_loop) != len(vbus_loop_geometry):
        raise RuntimeError("only part of the legacy VBUS U-turn was found")
    if vbus_loop:
        width = vbus_loop[0].GetWidth()
        net_code = vbus_loop[0].GetNetCode()
        for track in vbus_loop:
            board.Remove(track)
            tracks.remove(track)
        tracks.append(
            add_track(board, vbus_entry, vbus_exit, width, pcbnew.F_Cu, net_code)
        )

    # These two pad-free waypoints are genuine overshoots rather than
    # clearance jogs.  COL4 ran 17.18 mm past its junction and doubled back
    # 4.33 mm; SW20's LED-data route overshot its junction by 0.60 mm.
    # Replace only the exact reviewed geometry so this cleanup cannot silently
    # alter a future reroute.
    col4_u_turn = replace_exact_u_turn(
        board,
        tracks,
        "COL4",
        pcbnew.B_Cu,
        (138.625, 131.450798),
        (138.625, 114.275),
        (138.625, 118.6),
    )
    sw20_u_turn = replace_exact_u_turn(
        board,
        tracks,
        "Net-(SW20-Pad4)",
        pcbnew.B_Cu,
        (131.4, 112.8),
        (136.6, 112.8),
        (136.000001, 112.8),
    )
    col3_detour = replace_exact_chain(
        board,
        tracks,
        "COL3",
        pcbnew.B_Cu,
        [
            (78.2, 116.8),
            (84.0, 122.6),
            (79.632031, 122.6),
            (80.832031, 123.8),
            (85.2, 123.8),
        ],
    )
    enc_a_detour = replace_exact_chain(
        board,
        tracks,
        "ENC_A",
        pcbnew.B_Cu,
        [
            (107.7172, 108.3672),
            (109.0, 109.65),
            (106.0, 109.65),
        ],
    )

    # Exact non-zero duplicates do not add connectivity and can create narrow
    # rendering artifacts. Zero-length endpoint records are retained because
    # KiCad uses several of them on the reversible pads.
    unique: dict[tuple[object, ...], object] = {}
    duplicates = []
    for track in tracks:
        start, end = point(track.GetStart()), point(track.GetEnd())
        key = (
            track.GetNetCode(),
            track.GetLayer(),
            track.GetWidth(),
            min(start, end),
            max(start, end),
        )
        if start != end and key in unique:
            duplicates.append(track)
        else:
            unique[key] = track
    for track in duplicates:
        board.Remove(track)
    tracks = [track for track in tracks if track not in duplicates]

    grouped: dict[tuple[int, int, int], list[object]] = defaultdict(list)
    for track in tracks:
        if track.GetNetname() == rgb_net_name and track.GetLayer() == pcbnew.F_Cu:
            continue
        grouped[(track.GetNetCode(), track.GetLayer(), track.GetWidth())].append(track)

    replaced = 0
    created = 0
    for (net_code, layer, width), route_tracks in grouped.items():
        net_name = route_tracks[0].GetNetname()
        group_tolerance_mm = min(
            tolerance_mm,
            TOLERANCE_LIMITS_MM.get((net_name, layer), tolerance_mm),
        )
        adjacency: dict[tuple[int, int], list[int]] = defaultdict(list)
        for index, track in enumerate(route_tracks):
            adjacency[point(track.GetStart())].append(index)
            adjacency[point(track.GetEnd())].append(index)

        breakpoints = {
            route_point
            for route_point, edges in adjacency.items()
            if len(edges) != 2
        }
        breakpoints.update(
            point(via.GetPosition()) for via in vias if via.GetNetCode() == net_code
        )
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                if pad.GetNetCode() == net_code and pad.GetLayerSet().Contains(layer):
                    breakpoints.add(point(pad.GetPosition()))

        seen_edges: set[int] = set()
        chains: list[tuple[list[int], list[tuple[int, int]]]] = []
        for start in breakpoints:
            for first_edge in adjacency.get(start, []):
                if first_edge in seen_edges:
                    continue
                points = [start]
                edges = []
                current = start
                edge = first_edge
                while True:
                    seen_edges.add(edge)
                    edges.append(edge)
                    track = route_tracks[edge]
                    first = point(track.GetStart())
                    second = point(track.GetEnd())
                    following = second if first == current else first
                    points.append(following)
                    if following in breakpoints:
                        break
                    remaining = [
                        candidate
                        for candidate in adjacency[following]
                        if candidate not in seen_edges
                    ]
                    if not remaining:
                        break
                    current = following
                    edge = remaining[0]
                chains.append((edges, points))

        for edges, points in chains:
            if len(edges) < 2 or points[0] == points[-1] or not touches_thumb_region(points):
                continue
            simplified = simplify_polyline(points, pcbnew.FromMM(group_tolerance_mm))
            if len(simplified) >= len(points):
                continue
            for edge in edges:
                board.Remove(route_tracks[edge])
            replaced += len(edges)
            for start, end in zip(simplified, simplified[1:]):
                add_track(board, start, end, width, layer, net_code)
                created += 1

    if not rgb_already_clean:
        if not rgb_backtrack:
            raise RuntimeError("SW19-to-SW26 F.Cu backtrack was not found")
        for track in rgb_backtrack:
            board.Remove(track)
        for start, end in zip(rgb_route_points, rgb_route_points[1:]):
            add_track(
                board,
                start,
                end,
                pcbnew.FromMM(0.20),
                pcbnew.F_Cu,
                rgb_net_code,
            )

    for drawing in legacy_silkscreen:
        board.Remove(drawing)

    return (
        len(duplicates),
        replaced,
        created,
        0 if rgb_already_clean else len(rgb_backtrack),
        len(vbus_loop),
        col4_u_turn,
        sw20_u_turn,
        col3_detour,
        enc_a_detour,
        len(legacy_silkscreen),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--output", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE_MM)
    args = parser.parse_args()

    board = pcbnew.LoadBoard(str(args.input))
    (
        duplicates,
        replaced,
        created,
        backtrack,
        vbus_loop,
        col4_u_turn,
        sw20_u_turn,
        col3_detour,
        enc_a_detour,
        silkscreen,
    ) = simplify_routes(board, args.tolerance)
    pcbnew.SaveBoard(str(args.output), board)
    print(
        "Routing cleanup: "
        f"{duplicates} duplicates removed, {replaced} fragments replaced by "
        f"{created} segments, {backtrack} backtracking segments replaced, "
        f"{vbus_loop} VBUS U-turn segments replaced, "
        f"{col4_u_turn} COL4 U-turn segments replaced, "
        f"{sw20_u_turn} SW20 U-turn segments replaced, "
        f"{col3_detour} COL3 detour segments replaced, "
        f"{enc_a_detour} ENC_A detour segments replaced, "
        f"{silkscreen} legacy silkscreen bars removed"
    )


if __name__ == "__main__":
    main()
