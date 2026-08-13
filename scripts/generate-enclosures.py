#!/usr/bin/env python3
"""Generate acrylic plate packages and a conservative 2.5D CNC aluminum case."""

from __future__ import annotations

import json
import math
import shutil
import tempfile
import zipfile
from pathlib import Path

try:
    import cadquery as cq
    import ezdxf
    from shapely.geometry import Polygon
except ImportError as error:
    raise SystemExit(
        "CadQuery is required. Run `npm run generate:enclosures`, or install "
        "requirements-cad.txt into a Python 3.12 environment."
    ) from error


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
MANUFACTURING = OUTPUT / "manufacturing"
CONFIG = json.loads((ROOT / "layout.config.json").read_text())
POSITIONS = json.loads((OUTPUT / "key-positions.json").read_text())
MECHANICAL = CONFIG["mechanical"]
ACRYLIC = MECHANICAL["acrylic"]
CASE = MECHANICAL["cncCase"]
TRRS = CONFIG["trrs"]


def transformed(point: dict, mirror_axis: float | None = None) -> tuple[float, float]:
    x = point["x"]
    if mirror_axis is not None:
        x = mirror_axis - x
    return x, point["y"]


def outline_wire(mirror_axis: float | None = None) -> cq.Wire:
    points = MECHANICAL["boardOutline"]
    edges = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        controls = [
            transformed(start, mirror_axis),
            transformed(start["controlOut"], mirror_axis),
            transformed(end["controlIn"], mirror_axis),
            transformed(end, mirror_axis),
        ]
        edges.append(cq.Edge.makeBezier([cq.Vector(x, y, 0) for x, y in controls]))
    wire = cq.Wire.assembleEdges(edges)
    if not wire.IsClosed():
        raise RuntimeError("The enclosure source outline is not closed")
    return wire


def sampled_outline(mirror_axis: float | None = None, samples_per_segment: int = 40) -> list[tuple[float, float]]:
    result = []
    points = MECHANICAL["boardOutline"]
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        controls = [start, start["controlOut"], end["controlIn"], end]
        for sample in range(samples_per_segment):
            t = sample / samples_per_segment
            u = 1 - t
            x = u**3 * controls[0]["x"] + 3*u*u*t*controls[1]["x"] + 3*u*t*t*controls[2]["x"] + t**3*controls[3]["x"]
            y = u**3 * controls[0]["y"] + 3*u*u*t*controls[1]["y"] + 3*u*t*t*controls[2]["y"] + t**3*controls[3]["y"]
            if mirror_axis is not None:
                x = mirror_axis - x
            result.append((x, y))
    return result


def expanded_wire(points: list[tuple[float, float]], distance: float) -> cq.Wire:
    source = Polygon(points)
    if not source.is_valid:
        source = source.buffer(0)
    offset = source.buffer(distance, quad_segs=16, join_style="round")
    if offset.is_empty or offset.geom_type != "Polygon":
        raise RuntimeError(f"Unable to offset enclosure outline by {distance} mm")
    coordinates = list(offset.exterior.coords)[:-1]
    return cq.Wire.makePolygon([cq.Vector(x, y, 0) for x, y in coordinates], close=True)


def extrude_wire(wire: cq.Wire, height: float, z: float = 0) -> cq.Workplane:
    face = cq.Face.makeFromWires(wire)
    return cq.Workplane(obj=face).extrude(height).translate((0, 0, z))


def cylinder(center: tuple[float, float], diameter: float, height: float, z: float = 0) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .center(*center)
        .circle(diameter / 2)
        .extrude(height)
        .translate((0, 0, z))
    )


def rounded_rectangle(center: tuple[float, float], width: float, height: float, radius: float, depth: float, z: float = 0) -> cq.Workplane:
    horizontal = (
        cq.Workplane("XY").center(*center).rect(width - 2 * radius, height).extrude(depth)
    )
    vertical = (
        cq.Workplane("XY").center(*center).rect(width, height - 2 * radius).extrude(depth)
    )
    result = horizontal.union(vertical)
    for x in (center[0] - width / 2 + radius, center[0] + width / 2 - radius):
        for y in (center[1] - height / 2 + radius, center[1] + height / 2 - radius):
            result = result.union(cylinder((x, y), radius * 2, depth))
    return result.translate((0, 0, z))


def side_geometry(side: str) -> dict:
    mirror_axis = None if side == "left" else POSITIONS["right"][0]["x"] + POSITIONS["left"][0]["x"]
    transform = lambda point: transformed(point, mirror_axis)
    electronics = ACRYLIC["electronicsWindow"]
    center = transform({"x": electronics["centerX"], "y": electronics["centerY"]})
    trrs_slot = TRRS["plateSlot"]
    return {
        "mirrorAxis": mirror_axis,
        "outline": outline_wire(mirror_axis),
        "outlinePoints": sampled_outline(mirror_axis),
        "holes": [transform(point) for point in MECHANICAL["mountingHoles"]],
        "reset": transform(MECHANICAL["resetAccess"]),
        "electronics": center,
        "trrsSlot": transform({"x": trrs_slot["centerX"], "y": trrs_slot["centerY"]}),
        "keys": POSITIONS[side],
    }


def make_switch_plate(geometry: dict) -> cq.Workplane:
    thickness = CASE["topPlateThickness"]
    plate = extrude_wire(geometry["outline"], thickness)
    cut_depth = thickness + 2
    for key in geometry["keys"]:
        if key["group"] == "encoder":
            cutter = cylinder((key["x"], key["y"]), CONFIG["encoder"]["plateHoleDiameter"], cut_depth, -1)
        else:
            cutter = (
                cq.Workplane("XY")
                .transformed(offset=(key["x"], key["y"], -1), rotate=(0, 0, key["rotation"]))
                .rect(CONFIG["switch"]["plateCutout"], CONFIG["switch"]["plateCutout"])
                .extrude(cut_depth)
            )
        plate = plate.cut(cutter)
    for hole in geometry["holes"]:
        plate = plate.cut(cylinder(hole, ACRYLIC["mountingHoleDiameter"], cut_depth, -1))
    window = ACRYLIC["electronicsWindow"]
    plate = plate.cut(
        rounded_rectangle(
            geometry["electronics"],
            window["width"],
            window["height"],
            window["cornerRadius"],
            cut_depth,
            -1,
        )
    )
    trrs_slot = TRRS["plateSlot"]
    plate = plate.cut(
        rounded_rectangle(
            geometry["trrsSlot"],
            trrs_slot["width"],
            trrs_slot["height"],
            trrs_slot["cornerRadius"],
            cut_depth,
            -1,
        )
    )
    return plate


def make_case_base(geometry: dict) -> cq.Workplane:
    outer = expanded_wire(geometry["outlinePoints"], CASE["outerWall"])
    pocket = expanded_wire(geometry["outlinePoints"], CASE["pcbPerimeterClearance"])
    body = extrude_wire(outer, CASE["overallHeight"])
    body = body.cut(
        extrude_wire(
            pocket,
            CASE["overallHeight"] - CASE["floorThickness"] + 1,
            CASE["floorThickness"],
        )
    )
    trrs_slot = TRRS["plateSlot"]
    notch_bottom = TRRS["caseNotchBottom"]
    body = body.cut(
        rounded_rectangle(
            geometry["trrsSlot"],
            trrs_slot["width"],
            trrs_slot["height"],
            trrs_slot["cornerRadius"],
            CASE["overallHeight"] - notch_bottom + 1,
            notch_bottom,
        )
    )
    boss_height = CASE["pcbUndersideHeight"] - CASE["floorThickness"]
    for hole in geometry["holes"]:
        body = body.union(cylinder(hole, CASE["bossDiameter"], boss_height, CASE["floorThickness"]))
        drill_start = CASE["pcbUndersideHeight"] - CASE["threadDepth"]
        body = body.cut(
            cylinder(
                hole,
                CASE["tapDrillDiameter"],
                CASE["threadDepth"] + 0.25,
                drill_start,
            )
        )
    body = body.cut(
        cylinder(
            geometry["reset"],
            CASE["resetAccessDiameter"],
            CASE["overallHeight"] + 2,
            -1,
        )
    )
    return body


def ordered_wire_points(wire: cq.Wire, samples_per_edge: int = 24) -> list[tuple[float, float]]:
    points = []
    for edge in wire.Edges():
        sampled = [edge.positionAt(index / (samples_per_edge - 1)) for index in range(samples_per_edge)]
        if points:
            start = (sampled[0].x, sampled[0].y)
            end = (sampled[-1].x, sampled[-1].y)
            if math.dist(points[-1], end) < math.dist(points[-1], start):
                sampled.reverse()
        for point in sampled[:-1]:
            candidate = (point.x, point.y)
            if not points or math.dist(points[-1], candidate) > 1e-6:
                points.append(candidate)
    return points


def write_case_dxf(path: Path, geometry: dict) -> None:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for name, color in (("OUTER_PROFILE", 7), ("PCB_POCKET", 3), ("BOSSES", 4), ("M2_TAP_DRILL", 1), ("RESET_ACCESS", 6), ("TRRS_CABLE_CLEARANCE", 2)):
        doc.layers.add(name, color=color)
    model = doc.modelspace()
    outer = expanded_wire(geometry["outlinePoints"], CASE["outerWall"])
    pocket = expanded_wire(geometry["outlinePoints"], CASE["pcbPerimeterClearance"])
    model.add_lwpolyline(ordered_wire_points(outer), close=True, dxfattribs={"layer": "OUTER_PROFILE"})
    model.add_lwpolyline(ordered_wire_points(pocket), close=True, dxfattribs={"layer": "PCB_POCKET"})
    for hole in geometry["holes"]:
        model.add_circle(hole, CASE["bossDiameter"] / 2, dxfattribs={"layer": "BOSSES"})
        model.add_circle(hole, CASE["tapDrillDiameter"] / 2, dxfattribs={"layer": "M2_TAP_DRILL"})
    model.add_circle(geometry["reset"], CASE["resetAccessDiameter"] / 2, dxfattribs={"layer": "RESET_ACCESS"})
    trrs_slot = TRRS["plateSlot"]
    slot_wire = rounded_rectangle(
        geometry["trrsSlot"],
        trrs_slot["width"],
        trrs_slot["height"],
        trrs_slot["cornerRadius"],
        1,
    ).faces(">Z").wires().val()
    model.add_lwpolyline(
        ordered_wire_points(slot_wire),
        close=True,
        dxfattribs={"layer": "TRRS_CABLE_CLEARANCE"},
    )
    doc.saveas(path)


def write_section_svg(path: Path) -> None:
    body_height = CASE["overallHeight"]
    floor = CASE["floorThickness"]
    pcb_under = CASE["pcbUndersideHeight"]
    pcb_top = pcb_under + 1.6
    plate_under = pcb_top + CASE["pcbToPlateGap"]
    plate_top = plate_under + CASE["topPlateThickness"]
    scale = 18
    width = 150
    height = 250
    baseline = 220
    def y(z):
        return baseline - z * scale
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="150mm" height="75mm" viewBox="0 0 {width} {height}">
  <style>text{{font:8px sans-serif;fill:#222}} .dim{{stroke:#555;stroke-width:1;fill:none}} .case{{fill:#bbb;stroke:#222}} .pcb{{fill:#2c6b45;stroke:#173b27}} .plate{{fill:#8fb6d9;stroke:#365d80;fill-opacity:.7}}</style>
  <rect class="case" x="20" y="{y(body_height)}" width="110" height="{body_height*scale}" />
  <rect fill="#fff" x="38" y="{y(body_height)+1}" width="74" height="{(body_height-floor)*scale-1}" />
  <rect class="case" x="56" y="{y(pcb_under)}" width="16" height="{(pcb_under-floor)*scale}" />
  <rect class="pcb" x="32" y="{y(pcb_top)}" width="86" height="{1.6*scale}" />
  <rect class="plate" x="25" y="{y(plate_top)}" width="100" height="{CASE['topPlateThickness']*scale}" />
  <path class="dim" d="M 136 {y(0)} V {y(plate_top)}" />
  <text x="5" y="20">Arc 58 CNC case nominal section (mm)</text>
  <text x="74" y="{y(floor)+10}">floor {floor}</text>
  <text x="74" y="{y(pcb_under)-4}">PCB underside Z {pcb_under}</text>
  <text x="74" y="{y(pcb_top)-4}">PCB top Z {pcb_top}</text>
  <text x="74" y="{y(plate_under)-4}">plate underside Z {plate_under}</text>
  <text x="74" y="{y(plate_top)-4}">assembled top Z {plate_top}</text>
</svg>'''
    path.write_text(svg)


def export_step(shape: cq.Workplane | cq.Assembly, path: Path) -> None:
    if isinstance(shape, cq.Assembly):
        shape.save(str(path))
    else:
        cq.exporters.export(shape, str(path))
    if path.stat().st_size < 1024:
        raise RuntimeError(f"STEP export is unexpectedly small: {path}")


def validate_step(path: Path, minimum_volume: float) -> tuple[float, tuple[float, float, float]]:
    imported = cq.importers.importStep(str(path))
    solids = imported.solids().vals()
    if not solids:
        raise RuntimeError(f"No solid found in {path.name}")
    volume = sum(solid.Volume() for solid in solids)
    box = imported.val().BoundingBox()
    if volume < minimum_volume:
        raise RuntimeError(f"Volume check failed for {path.name}: {volume:.1f} mm^3")
    return volume, (box.xlen, box.ylen, box.zlen)


def acrylic_readme() -> str:
    return f"""# Hamrah Arc 58 Rev {CONFIG['revision']} acrylic plates

All geometry is 1:1 in millimetres. Order one left and one right file for each
layer; do not mirror files at the laser cutter.

- Top plates: {ACRYLIC['topThickness']} mm cast acrylic, with 14.0 mm Choc v1 cutouts,
  one boolean-merged controller/OLED and {TRRS['plugClearanceDiameter']} mm-high TRRS edge notch,
  an encoder opening, and 2.4 mm M2 clearance holes.
- Bottom plates: {ACRYLIC['bottomThickness']} mm cast acrylic, with 2.4 mm M2 clearance holes
  and a {ACRYLIC['resetAccessDiameter']} mm reset opening.
- Use the supplied 13.8/14.0/14.2 mm fit coupon in the exact stock, color, and
  laser process before releasing the full plates. The nominal plates use 14.0 mm.
- Ask the vendor to manage kerf; do not scale or add a second compensation.
- General profile tolerance: +/-0.15 mm. Switch cutouts and mounting-hole
  locations: +/-0.10 mm. Remove protective film only after assembly.

The top plate is designed to sit nominally 2.2 mm above the PCB. Dry-fit the
actual Choc switch batch before choosing final sleeves/washers. Keep at least
3.5 mm between the PCB underside and bottom plate for hotswap sockets, diodes,
and RGB components. This is Rev {CONFIG['revision']} prototype tooling and should be verified
against a fabricated PCB before ordering decorative materials in quantity.
"""


def cnc_readme(case_dimensions: dict) -> str:
    return f"""# Hamrah Arc 58 Rev {CONFIG['revision']} CNC aluminum case

This package contains separate left/right 6061-T6 aluminum bottom chassis and
1.5 mm switch plates. The switch plate can be replaced with the acrylic top
plate from the companion package. STEP is the authoritative 3D geometry; DXF
files are annotated top-view references, not substitutes for the STEP model.

Nominal construction:

- Material: {CASE['material']}; bead blast plus anodize is optional.
- Bottom chassis overall size: {case_dimensions['x']:.3f} x {case_dimensions['y']:.3f} x {CASE['overallHeight']:.3f} mm.
- Exterior wall allowance: {CASE['outerWall']} mm outside the PCB outline.
- PCB pocket clearance: {CASE['pcbPerimeterClearance']} mm per side.
- Floor: {CASE['floorThickness']} mm; PCB underside support plane: Z={CASE['pcbUndersideHeight']} mm.
- Six integral bosses: diameter {CASE['bossDiameter']} mm.
- Boss holes: drill {CASE['tapDrillDiameter']} mm and tap {CASE['thread']} to {CASE['threadDepth']} mm depth.
- Reset access: {CASE['resetAccessDiameter']} mm through the floor.
- Switch plate: {CASE['topPlateThickness']} mm, 14.0 mm Choc v1 openings,
  2.4 mm M2 clearance holes, and one boolean-merged controller/OLED and
  {TRRS['plugClearanceDiameter']} mm-high TRRS edge notch.
- Plate underside: Z={CASE['pcbUndersideHeight'] + 1.6 + CASE['pcbToPlateGap']:.3f} mm in the reference assembly.

Manufacturing notes:

- General tolerance +/-0.125 mm; mounting positions and switch openings
  +/-0.10 mm. Do not apply a global scale factor.
- Use a 1.0 mm internal floor radius or the shop's standard small end-mill
  radius. Break exposed edges R0.5 maximum and deburr all holes.
- Mask threaded holes during anodizing and chase the M2 threads afterward.
- The TRRS jack faces the inner split edge. Machine the open cable notch from
  Z={TRRS['caseNotchBottom']} mm through the top rim; it clears a nominal
  {TRRS['plugClearanceDiameter']} mm-diameter plug housing.
- Order one left and one right chassis. Do not mirror at the machine shop.
- Prototype the PCB and acrylic stack first. Rev {CONFIG['revision']} has passed design-rule
  checks but has not yet completed physical keyboard bring-up.
"""


def write_zip(path: Path, files: list[tuple[Path, str]], readme: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", readme)
        for source, name in files:
            archive.write(source, name)
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"ZIP integrity check failed at {bad}")


def main() -> None:
    MANUFACTURING.mkdir(parents=True, exist_ok=True)
    expected_plate_files = [
        "left-half-plate.dxf", "right-half-plate.dxf",
        "left-half-bottom-plate.dxf", "right-half-bottom-plate.dxf",
        "left-half-plate.svg", "right-half-plate.svg",
        "left-half-bottom-plate.svg", "right-half-bottom-plate.svg",
        "choc-v1-acrylic-fit-coupon.dxf", "choc-v1-acrylic-fit-coupon.svg",
    ]
    missing = [name for name in expected_plate_files if not (OUTPUT / name).exists()]
    if missing:
        raise RuntimeError(f"Run `npm run generate` first; missing: {', '.join(missing)}")

    acrylic_names = {
        "left-half-plate.dxf": "left-top-plate-1p5mm.dxf",
        "right-half-plate.dxf": "right-top-plate-1p5mm.dxf",
        "left-half-bottom-plate.dxf": "left-bottom-plate-3mm.dxf",
        "right-half-bottom-plate.dxf": "right-bottom-plate-3mm.dxf",
        "left-half-plate.svg": "previews/left-top-plate.svg",
        "right-half-plate.svg": "previews/right-top-plate.svg",
        "left-half-bottom-plate.svg": "previews/left-bottom-plate.svg",
        "right-half-bottom-plate.svg": "previews/right-bottom-plate.svg",
        "choc-v1-acrylic-fit-coupon.dxf": "choc-v1-fit-coupon.dxf",
        "choc-v1-acrylic-fit-coupon.svg": "previews/choc-v1-fit-coupon.svg",
    }
    revision_slug = CONFIG["revision"].lower()
    acrylic_zip = MANUFACTURING / f"arc58-acrylic-plates-rev-{revision_slug}.zip"
    write_zip(
        acrylic_zip,
        [(OUTPUT / source, target) for source, target in acrylic_names.items()],
        acrylic_readme(),
    )

    with tempfile.TemporaryDirectory(prefix="arc58-cnc-") as temp_name:
        temp = Path(temp_name)
        package_files = []
        side_results = {}
        section = temp / "case-nominal-section.svg"
        write_section_svg(section)
        package_files.append((section, section.name))
        for side in ("left", "right"):
            geometry = side_geometry(side)
            case_base = make_case_base(geometry)
            switch_plate = make_switch_plate(geometry)
            base_step = temp / f"{side}-cnc-bottom-chassis.step"
            plate_step = temp / f"{side}-cnc-switch-plate-1p5mm.step"
            assembly_step = temp / f"{side}-case-assembly-REFERENCE.step"
            drawing_dxf = temp / f"{side}-cnc-bottom-chassis-top-view.dxf"
            export_step(case_base, base_step)
            export_step(switch_plate, plate_step)
            plate_z = CASE["pcbUndersideHeight"] + 1.6 + CASE["pcbToPlateGap"]
            assembly = cq.Assembly(name=f"arc58-{side}-case-reference")
            assembly.add(case_base, name="bottom-chassis", color=cq.Color(0.25, 0.25, 0.28))
            assembly.add(switch_plate.translate((0, 0, plate_z)), name="switch-plate", color=cq.Color(0.65, 0.68, 0.72))
            assembly.add(extrude_wire(geometry["outline"], 1.6, CASE["pcbUndersideHeight"]), name="pcb-envelope", color=cq.Color(0.10, 0.45, 0.22, 0.65))
            export_step(assembly, assembly_step)
            write_case_dxf(drawing_dxf, geometry)
            volume, dimensions = validate_step(base_step, 25000)
            plate_volume, plate_dimensions = validate_step(plate_step, 10000)
            if abs(dimensions[2] - CASE["overallHeight"]) > 0.01:
                raise RuntimeError(f"{side} chassis height does not match configuration")
            if abs(plate_dimensions[2] - CASE["topPlateThickness"]) > 0.01:
                raise RuntimeError(f"{side} switch-plate height does not match configuration")
            side_results[side] = {
                "x": dimensions[0],
                "y": dimensions[1],
                "z": dimensions[2],
                "volume": volume,
                "plateVolume": plate_volume,
            }
            package_files.extend([
                (base_step, base_step.name),
                (plate_step, plate_step.name),
                (assembly_step, f"reference/{assembly_step.name}"),
                (drawing_dxf, f"drawings/{drawing_dxf.name}"),
                (OUTPUT / f"{side}-half-plate.dxf", f"drawings/{side}-switch-plate-waterjet.dxf"),
            ])
        left = side_results["left"]
        right = side_results["right"]
        for property_name in ("x", "y", "z", "volume", "plateVolume"):
            if abs(left[property_name] - right[property_name]) > 0.01:
                raise RuntimeError(
                    f"Mirrored case mismatch for {property_name}: "
                    f"left={left[property_name]:.4f}, right={right[property_name]:.4f}"
                )
        specification = temp / "case-specifications.json"
        specification.write_text(json.dumps({"revision": CONFIG["revision"], "units": "mm", "acrylic": ACRYLIC, "cncCase": CASE, "trrs": TRRS, "generatedDimensions": side_results}, indent=2) + "\n")
        package_files.append((specification, specification.name))
        cnc_zip = MANUFACTURING / f"arc58-cnc-aluminum-case-rev-{revision_slug}.zip"
        write_zip(cnc_zip, package_files, cnc_readme(left))

    print(f"PASS: wrote {acrylic_zip}")
    print(f"PASS: wrote {cnc_zip}")


if __name__ == "__main__":
    main()
