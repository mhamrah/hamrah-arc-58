import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  boundsForPoints,
  buildHalf,
  closedOutlineSegments,
  mirrorKey,
  readConfig,
  rectangleCorners,
  sampleClosedCurve
} from "./layout-model.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const rootDirectory = path.resolve(scriptDirectory, "..");
const outputDirectory = path.join(rootDirectory, "output");
const config = readConfig();
const leftKeys = buildHalf(config);
const outlineSegments = closedOutlineSegments(config.mechanical);
const leftOutline = sampleClosedCurve(outlineSegments);
const halfBounds = boundsForPoints(leftOutline);
const halfWidth = halfBounds.maxX - halfBounds.minX;
const halfHeight = halfBounds.maxY - halfBounds.minY;
const manufacturingBounds = halfBounds;

fs.mkdirSync(outputDirectory, { recursive: true });

function format(value) {
  return Number(value.toFixed(3));
}

function pointsAttribute(points) {
  return points.map((point) => `${format(point.x)},${format(point.y)}`).join(" ");
}

function roundedRectanglePoints(center, width, height, radius, stepsPerCorner = 8) {
  const halfWidth = width / 2;
  const halfHeight = height / 2;
  const corners = [
    { x: center.x + halfWidth - radius, y: center.y - halfHeight + radius, start: -90 },
    { x: center.x + halfWidth - radius, y: center.y + halfHeight - radius, start: 0 },
    { x: center.x - halfWidth + radius, y: center.y + halfHeight - radius, start: 90 },
    { x: center.x - halfWidth + radius, y: center.y - halfHeight + radius, start: 180 }
  ];
  return corners.flatMap((corner) =>
    Array.from({ length: stepsPerCorner + 1 }, (_, index) => {
      const angle = ((corner.start + (90 * index) / stepsPerCorner) * Math.PI) / 180;
      return {
        x: corner.x + radius * Math.cos(angle),
        y: corner.y + radius * Math.sin(angle)
      };
    })
  );
}

function transformCurve(segments, transform) {
  const point = (value) => transform(value);
  return segments.map((segment) => ({
    start: point(segment.start),
    control1: point(segment.control1),
    control2: point(segment.control2),
    end: point(segment.end)
  }));
}

function curvePath(segments) {
  const first = segments[0].start;
  const commands = [`M ${format(first.x)} ${format(first.y)}`];
  for (const segment of segments) {
    commands.push(
      `C ${format(segment.control1.x)} ${format(segment.control1.y)} ` +
      `${format(segment.control2.x)} ${format(segment.control2.y)} ` +
      `${format(segment.end.x)} ${format(segment.end.y)}`
    );
  }
  commands.push("Z");
  return commands.join(" ");
}

function svgComponent(key, side, offsetX, mirrorAxis = null) {
  const displayKey = mirrorAxis === null ? key : mirrorKey(key, mirrorAxis);
  const x = displayKey.x + offsetX;
  const y = displayKey.y;
  const className = `key key--${key.group}`;
  const label =
    key.group === "thumb"
      ? `T${key.index + 1}`
      : key.group === "encoder"
        ? "ENC"
        : key.id.toUpperCase();
  if (key.group === "encoder") {
    return `
    <g class="${className}" transform="translate(${format(x)} ${format(y)})">
      <circle class="encoder-knob" r="${format(config.encoder.knobDiameter / 2)}" />
      <rect class="encoder-body" x="${format(-config.encoder.bodyWidth / 2)}" y="${format(-config.encoder.bodyHeight / 2)}" width="${config.encoder.bodyWidth}" height="${config.encoder.bodyHeight}" rx="1" />
      <circle class="cutout" r="${format(config.encoder.plateHoleDiameter / 2)}" />
      <circle class="center" r="0.6" />
      <text y="0.9">${side}${label}</text>
    </g>`;
  }
  return `
    <g class="${className}" transform="translate(${format(x)} ${format(y)}) rotate(${format(displayKey.rotation)})">
      <rect class="keycap" x="${format(-config.switch.keycapWidth / 2)}" y="${format(-config.switch.keycapHeight / 2)}" width="${config.switch.keycapWidth}" height="${config.switch.keycapHeight}" rx="1.6" />
      <rect class="cutout" x="${format(-config.switch.plateCutout / 2)}" y="${format(-config.switch.plateCutout / 2)}" width="${config.switch.plateCutout}" height="${config.switch.plateCutout}" />
      <circle class="center" r="0.6" />
      <text transform="rotate(${format(-displayKey.rotation)})" y="0.9">${side}${label}</text>
    </g>`;
}

function makeFullSvg() {
  const pageMargin = 12;
  const gap = config.preview.splitGap;
  const leftOffsetX = pageMargin - halfBounds.minX;
  const rightStart = pageMargin + halfWidth + gap;
  const rightMirrorAxis = halfBounds.minX + halfBounds.maxX;
  const rightOffsetX = rightStart - halfBounds.minX;
  const offsetY = pageMargin - halfBounds.minY + 11;
  const pageWidth = halfWidth * 2 + gap + pageMargin * 2;
  const pageHeight = halfHeight + pageMargin * 2 + 21;

  const shiftedLeftOutline = transformCurve(outlineSegments, (point) => ({
    x: point.x + leftOffsetX,
    y: point.y + offsetY
  }));
  const shiftedRightOutline = transformCurve(outlineSegments, (point) => ({
    x: rightMirrorAxis - point.x + rightOffsetX,
    y: point.y + offsetY
  }));
  const leftKeyMarkup = leftKeys
    .map((key) => svgComponent({ ...key, y: key.y + offsetY }, "L·", leftOffsetX))
    .join("");
  const rightKeyMarkup = leftKeys
    .map((key) =>
      svgComponent(
        { ...key, y: key.y + offsetY },
        "R·",
        rightOffsetX,
        rightMirrorAxis
      )
    )
    .join("");

  const [columnA, columnB] = config.thumbArc.startBetweenColumns;
  const thumbOne = leftKeys.find((key) => key.id === "thumb1");
  const guideX = thumbOne.x + leftOffsetX;
  const guideTop =
    Math.max(
      config.matrix.columnStagger[columnA] +
        (config.matrix.rows - 1) * config.switch.pitchY,
      config.matrix.columnStagger[columnB] +
        (config.matrix.rows - 1) * config.switch.pitchY
    ) + offsetY;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${format(pageWidth)}mm" height="${format(pageHeight)}mm" viewBox="0 0 ${format(pageWidth)} ${format(pageHeight)}">
  <title>${config.name} physical layout</title>
  <desc>Mirrored split layout with 56 ${config.switch.type} switches and two clickable encoders. All dimensions are millimetres.</desc>
  <style>
    :root { color-scheme: light; }
    .page { fill: #f4f1eb; }
    .plate { fill: #27313a; stroke: #13191e; stroke-width: 0.8; }
    .keycap { fill: #fbfaf7; stroke: #b8b3a9; stroke-width: 0.5; }
    .key--thumb .keycap { fill: #dc795c; stroke: #a7432f; }
    .encoder-knob { fill: #e8dfcd; stroke: #8b806d; stroke-width: 0.5; }
    .encoder-body { fill: none; stroke: #9e9078; stroke-width: 0.35; }
    .cutout { fill: none; stroke: #65727d; stroke-width: 0.35; stroke-dasharray: 1.2 0.8; }
    .center { fill: #65727d; }
    text { fill: #253039; font: 2.5px ui-monospace, SFMono-Regular, Menlo, monospace; text-anchor: middle; dominant-baseline: middle; }
    .title { fill: #20282f; font: 700 7px ui-sans-serif, system-ui, sans-serif; }
    .subtitle { fill: #59636b; font: 3.1px ui-sans-serif, system-ui, sans-serif; }
    .guide { stroke: #dfb43a; stroke-width: 0.7; stroke-dasharray: 2 1.5; fill: none; }
    .guide-label { fill: #795e10; font: 2.8px ui-sans-serif, system-ui, sans-serif; text-anchor: start; }
  </style>
  <rect class="page" width="100%" height="100%" />
  <text class="title" x="${pageMargin}" y="9">${config.name}</text>
  <text class="subtitle" x="${pageMargin}" y="15">6×4 + clickable encoder + four-key descending thumb arc · Choc v1 · ${config.switch.pitchX} × ${config.switch.pitchY} mm Sofle pitch</text>
  <path class="plate" d="${curvePath(shiftedLeftOutline)}" />
  <path class="plate" d="${curvePath(shiftedRightOutline)}" />
  ${leftKeyMarkup}
  ${rightKeyMarkup}
  <path class="guide" d="M ${format(guideX)} ${format(guideTop)} L ${format(guideX)} ${format(thumbOne.y + offsetY)}" />
  <text class="guide-label" x="${format(guideX + 2)}" y="${format((guideTop + thumbOne.y + offsetY) / 2)}">T1 is ${config.thumbArc.startOffsetTowardOuterEdge} mm outward from C5 / C6 midpoint</text>
</svg>
`;
}

function mirroredPoint(point) {
  return { x: manufacturingBounds.minX + manufacturingBounds.maxX - point.x, y: point.y };
}

function halfMechanical(side) {
  const mirror = side === "right";
  const trrsSlot = config.trrs.plateSlot;
  const segments = mirror
    ? transformCurve(outlineSegments, mirroredPoint)
    : outlineSegments;
  return {
    label: mirror ? "right" : "left",
    keys: mirror
      ? leftKeys.map((key) => mirrorKey(key, halfBounds.minX + halfBounds.maxX))
      : leftKeys,
    segments,
    outline: sampleClosedCurve(segments),
    holes: mirror
      ? config.mechanical.mountingHoles.map(mirroredPoint)
      : config.mechanical.mountingHoles,
    reset: mirror ? mirroredPoint(config.mechanical.resetAccess) : config.mechanical.resetAccess,
    electronicsWindow: {
      ...config.mechanical.acrylic.electronicsWindow,
      ...(mirror
        ? { centerX: mirroredPoint({ x: config.mechanical.acrylic.electronicsWindow.centerX, y: 0 }).x }
        : {})
    },
    trrsSlot: {
      ...trrsSlot,
      ...(mirror
        ? { centerX: mirroredPoint({ x: trrsSlot.centerX, y: 0 }).x }
        : {})
    }
  };
}

function makePlateSvg(side = "left") {
  const half = halfMechanical(side);
  const bounds = boundsForPoints(half.outline);
  const margin = 3;
  const offsetX = margin - bounds.minX;
  const offsetY = margin - bounds.minY;
  const width = bounds.maxX - bounds.minX + margin * 2;
  const height = bounds.maxY - bounds.minY + margin * 2;
  const outline = transformCurve(half.segments, (point) => ({
    x: point.x + offsetX,
    y: point.y + offsetY
  }));

  const cutouts = half.keys
    .map((key) => {
      if (key.group === "encoder") {
        return `  <circle class="cut" data-key="${key.id}" cx="${format(key.x + offsetX)}" cy="${format(key.y + offsetY)}" r="${format(config.encoder.plateHoleDiameter / 2)}" />`;
      }
      const points = rectangleCorners(
        key,
        config.switch.plateCutout,
        config.switch.plateCutout
      ).map((point) => ({ x: point.x + offsetX, y: point.y + offsetY }));
      return `  <polygon class="cut" data-key="${key.id}" points="${pointsAttribute(points)}" />`;
    })
    .join("\n");
  const holes = half.holes
    .map((hole, index) => `  <circle class="cut" data-hole="H${index + 1}" cx="${format(hole.x + offsetX)}" cy="${format(hole.y + offsetY)}" r="${format(config.mechanical.acrylic.mountingHoleDiameter / 2)}" />`)
    .join("\n");
  const electronics = half.electronicsWindow;
  const trrsSlot = half.trrsSlot;

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${format(width)}mm" height="${format(height)}mm" viewBox="0 0 ${format(width)} ${format(height)}">
  <title>${config.name} ${half.label} acrylic top plate</title>
  <desc>One-to-one millimetre ${config.mechanical.acrylic.topThickness} mm cast-acrylic plate with electronics access, aligned to the Rev ${config.revision} reversible PCB.</desc>
  <style>
    .outline, .cut { fill: none; stroke: #000; stroke-width: 0.2; vector-effect: non-scaling-stroke; }
  </style>
  <path class="outline" d="${curvePath(outline)}" />
${cutouts}
${holes}
  <rect class="cut" data-cutout="controller-oled-trrs" x="${format(electronics.centerX - electronics.width / 2 + offsetX)}" y="${format(electronics.centerY - electronics.height / 2 + offsetY)}" width="${format(electronics.width)}" height="${format(electronics.height)}" rx="${format(electronics.cornerRadius)}" />
  <rect class="cut" data-cutout="trrs-cable-clearance" x="${format(trrsSlot.centerX - trrsSlot.width / 2 + offsetX)}" y="${format(trrsSlot.centerY - trrsSlot.height / 2 + offsetY)}" width="${format(trrsSlot.width)}" height="${format(trrsSlot.height)}" rx="${format(trrsSlot.cornerRadius)}" />
</svg>
`;
}

function makeBottomPlateSvg(side = "left") {
  const half = halfMechanical(side);
  const bounds = boundsForPoints(half.outline);
  const margin = 3;
  const offsetX = margin - bounds.minX;
  const offsetY = margin - bounds.minY;
  const width = bounds.maxX - bounds.minX + margin * 2;
  const height = bounds.maxY - bounds.minY + margin * 2;
  const outline = transformCurve(half.segments, (point) => ({
    x: point.x + offsetX,
    y: point.y + offsetY
  }));
  const holes = half.holes
    .map((hole, index) => `  <circle class="cut" data-hole="H${index + 1}" cx="${format(hole.x + offsetX)}" cy="${format(hole.y + offsetY)}" r="${format(config.mechanical.acrylic.mountingHoleDiameter / 2)}" />`)
    .join("\n");
  const reset = half.reset;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${format(width)}mm" height="${format(height)}mm" viewBox="0 0 ${format(width)} ${format(height)}">
  <title>${config.name} ${half.label} acrylic bottom plate</title>
  <desc>One-to-one millimetre ${config.mechanical.acrylic.bottomThickness} mm cast-acrylic bottom plate with reset access, aligned to the Rev ${config.revision} reversible PCB.</desc>
  <style>.outline, .cut { fill: none; stroke: #000; stroke-width: 0.2; vector-effect: non-scaling-stroke; }</style>
  <path class="outline" d="${curvePath(outline)}" />
${holes}
  <circle class="cut" data-cutout="reset" cx="${format(reset.x + offsetX)}" cy="${format(reset.y + offsetY)}" r="${format(config.mechanical.acrylic.resetAccessDiameter / 2)}" />
</svg>
`;
}

function makePaperTestSvg() {
  const pageWidth = 215.9;
  const pageHeight = 279.4;
  const templateTop = 32;
  const offsetX = (pageWidth - halfWidth) / 2 - halfBounds.minX;
  const offsetY = templateTop - halfBounds.minY;
  const outline = transformCurve(outlineSegments, (point) => ({
    x: point.x + offsetX,
    y: point.y + offsetY
  }));

  const keys = leftKeys
    .map((key) => {
      const x = key.x + offsetX;
      const y = key.y + offsetY;
      const label =
        key.group === "thumb"
          ? `T${key.index + 1}`
          : key.group === "encoder"
            ? "ENC"
            : `C${key.column + 1}R${key.row + 1}`;
      if (key.group === "encoder") {
        return `
    <g transform="translate(${format(x)} ${format(y)})">
      <circle class="encoder" r="${format(config.encoder.knobDiameter / 2)}" />
      <rect class="encoder-body" x="${format(-config.encoder.bodyWidth / 2)}" y="${format(-config.encoder.bodyHeight / 2)}" width="${config.encoder.bodyWidth}" height="${config.encoder.bodyHeight}" rx="1" />
      <path class="center" d="M -1.5 0 H 1.5 M 0 -1.5 V 1.5" />
      <text class="key-label" y="0.9">${label}</text>
    </g>`;
      }
      return `
    <g transform="translate(${format(x)} ${format(y)}) rotate(${format(key.rotation)})">
      <rect class="keycap ${key.group}" x="${format(-config.switch.keycapWidth / 2)}" y="${format(-config.switch.keycapHeight / 2)}" width="${config.switch.keycapWidth}" height="${config.switch.keycapHeight}" rx="1.2" />
      <path class="center" d="M -1.5 0 H 1.5 M 0 -1.5 V 1.5" />
      <text class="key-label" transform="rotate(${format(-key.rotation)})" y="0.9">${label}</text>
    </g>`;
    })
    .join("");

  const calibrationX = (pageWidth - 50) / 2;
  const calibrationY = templateTop + halfHeight + 20;

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${pageWidth}mm" height="${pageHeight}mm" viewBox="0 0 ${pageWidth} ${pageHeight}">
  <title>${config.name} left-half paper fit test</title>
  <desc>US Letter paper prototype. Print at actual size and verify the 50 mm calibration bar.</desc>
  <style>
    @page { size: Letter portrait; margin: 0; }
    .page { fill: #fff; }
    .outline { fill: #f7f7f7; stroke: #888; stroke-width: 0.35; }
    .keycap { fill: #fff; stroke: #111; stroke-width: 0.4; }
    .keycap.thumb { fill: #f4d5cc; }
    .encoder { fill: #eee8dc; stroke: #111; stroke-width: 0.4; }
    .encoder-body { fill: none; stroke: #777; stroke-width: 0.25; stroke-dasharray: 1 0.7; }
    .center { fill: none; stroke: #777; stroke-width: 0.25; }
    .key-label { fill: #222; font: 2.4px ui-monospace, SFMono-Regular, Menlo, monospace; text-anchor: middle; dominant-baseline: middle; }
    .title { fill: #111; font: 700 5px ui-sans-serif, system-ui, sans-serif; }
    .note { fill: #333; font: 3px ui-sans-serif, system-ui, sans-serif; }
    .calibration { fill: none; stroke: #111; stroke-width: 0.45; }
  </style>
  <rect class="page" width="100%" height="100%" />
  <text class="title" x="${format(pageWidth / 2)}" y="12" text-anchor="middle">${config.name} · left-half paper fit test</text>
  <text class="note" x="${format(pageWidth / 2)}" y="19" text-anchor="middle">Print at Actual Size / 100% · disable Fit to Page</text>
  <path class="outline" d="${curvePath(outline)}" />
  ${keys}
  <path class="calibration" d="M ${format(calibrationX)} ${format(calibrationY - 3)} V ${format(calibrationY + 3)} M ${format(calibrationX)} ${format(calibrationY)} H ${format(calibrationX + 50)} M ${format(calibrationX + 50)} ${format(calibrationY - 3)} V ${format(calibrationY + 3)}" />
  <text class="note" x="${format(pageWidth / 2)}" y="${format(calibrationY + 8)}" text-anchor="middle">This line must measure exactly 50 mm</text>
  <text class="note" x="${format(pageWidth / 2)}" y="${format(calibrationY + 17)}" text-anchor="middle">Rest your hand on the outline and test the T1–T4 thumb sweep.</text>
</svg>
`;
}

function dxfPolyline(points, layer, closed = true) {
  const header = ["0", "POLYLINE", "8", layer, "66", "1", "70", closed ? "1" : "0"];
  const vertices = points.flatMap((point) => [
    "0",
    "VERTEX",
    "8",
    layer,
    "10",
    String(format(point.x)),
    "20",
    String(format(-point.y)),
    "30",
    "0"
  ]);
  return [...header, ...vertices, "0", "SEQEND"].join("\n");
}

function dxfCircle(center, radius, layer) {
  return [
    "0",
    "CIRCLE",
    "8",
    layer,
    "10",
    String(format(center.x)),
    "20",
    String(format(-center.y)),
    "30",
    "0",
    "40",
    String(format(radius))
  ].join("\n");
}

function makeDxf(side = "left") {
  const half = halfMechanical(side);
  const entities = [dxfPolyline(half.outline, "PLATE_OUTLINE")];
  for (const key of half.keys) {
    if (key.group === "encoder") {
      entities.push(
        dxfCircle(key, config.encoder.plateHoleDiameter / 2, "ENCODER_CUTOUTS")
      );
      continue;
    }
    entities.push(
      dxfPolyline(
        rectangleCorners(
          key,
          config.switch.plateCutout,
          config.switch.plateCutout
        ),
        "SWITCH_CUTOUTS"
      )
    );
  }
  for (const hole of half.holes) {
    entities.push(dxfCircle(hole, config.mechanical.acrylic.mountingHoleDiameter / 2, "MOUNTING_HOLES"));
  }
  const electronics = half.electronicsWindow;
  entities.push(
    dxfPolyline(
      roundedRectanglePoints(
        { x: electronics.centerX, y: electronics.centerY },
        electronics.width,
        electronics.height,
        electronics.cornerRadius
      ),
      "ELECTRONICS_WINDOW"
    )
  );
  const trrsSlot = half.trrsSlot;
  entities.push(
    dxfPolyline(
      roundedRectanglePoints(
        { x: trrsSlot.centerX, y: trrsSlot.centerY },
        trrsSlot.width,
        trrsSlot.height,
        trrsSlot.cornerRadius
      ),
      "TRRS_CABLE_CLEARANCE"
    )
  );
  return [
    "0",
    "SECTION",
    "2",
    "HEADER",
    "9",
    "$INSUNITS",
    "70",
    "4",
    "0",
    "ENDSEC",
    "0",
    "SECTION",
    "2",
    "ENTITIES",
    ...entities,
    "0",
    "ENDSEC",
    "0",
    "EOF",
    ""
  ].join("\n");
}

function makeBottomDxf(side = "left") {
  const half = halfMechanical(side);
  const entities = [dxfPolyline(half.outline, "PLATE_OUTLINE")];
  for (const hole of half.holes) {
    entities.push(dxfCircle(hole, config.mechanical.acrylic.mountingHoleDiameter / 2, "MOUNTING_HOLES"));
  }
  entities.push(dxfCircle(half.reset, config.mechanical.acrylic.resetAccessDiameter / 2, "RESET_ACCESS"));
  return ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES", ...entities, "0", "ENDSEC", "0", "EOF", ""].join("\n");
}

function makeAcrylicFitCouponSvg() {
  const sizes = config.mechanical.acrylic.fitCouponCutouts;
  const width = 72;
  const height = 28;
  const centers = sizes.map((_, index) => ({ x: 14 + index * 22, y: 13 }));
  const cutouts = sizes.map((size, index) => {
    const center = centers[index];
    return `  <rect class="cut" x="${format(center.x - size / 2)}" y="${format(center.y - size / 2)}" width="${format(size)}" height="${format(size)}" />\n  <text x="${format(center.x)}" y="25.5">${format(size)} mm</text>`;
  }).join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}mm" height="${height}mm" viewBox="0 0 ${width} ${height}">
  <title>${config.name} Choc v1 acrylic fit coupon</title>
  <desc>Cut in the exact acrylic stock and process intended for the top plate, then choose the best switch fit.</desc>
  <style>.outline,.cut{fill:none;stroke:#000;stroke-width:.2;vector-effect:non-scaling-stroke} text{font:2px sans-serif;text-anchor:middle}</style>
  <rect class="outline" x="0.5" y="0.5" width="71" height="27" rx="2" />
${cutouts}
</svg>
`;
}

function makeAcrylicFitCouponDxf() {
  const sizes = config.mechanical.acrylic.fitCouponCutouts;
  const entities = [
    dxfPolyline(roundedRectanglePoints({ x: 36, y: 14 }, 71, 27, 2), "COUPON_OUTLINE")
  ];
  for (let index = 0; index < sizes.length; index += 1) {
    const size = sizes[index];
    entities.push(
      dxfPolyline(
        rectangleCorners({ x: 14 + index * 22, y: 13, rotation: 0 }, size, size),
        `CUTOUT_${String(size).replace(".", "_")}_MM`
      )
    );
  }
  return ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES", ...entities, "0", "ENDSEC", "0", "EOF", ""].join("\n");
}

function makePositionsJson() {
  const mirrorAxis = halfBounds.minX + halfBounds.maxX;
  return JSON.stringify(
    {
      name: config.name,
      units: config.units,
      switch: config.switch,
      encoder: config.encoder,
      notes: [
        "Coordinates are component centers.",
        "The right half is a geometric mirror of the left half.",
        "Each half has 28 Choc v1 switches and one clickable rotary encoder.",
        "This is layout and prototype plate geometry, not a routed PCB."
      ],
      left: leftKeys.map((key) => ({
        ...key,
        x: format(key.x),
        y: format(key.y),
        rotation: format(key.rotation)
      })),
      right: leftKeys.map((key) => {
        const mirrored = mirrorKey(key, mirrorAxis);
        return {
          ...mirrored,
          x: format(mirrored.x),
          y: format(mirrored.y),
          rotation: format(mirrored.rotation)
        };
      })
    },
    null,
    2
  );
}

const artifacts = {
  "keyboard-layout.svg": makeFullSvg(),
  "left-half-paper-test-letter.svg": makePaperTestSvg(),
  "left-half-plate.svg": makePlateSvg(),
  "left-half-plate.dxf": makeDxf(),
  "left-half-bottom-plate.svg": makeBottomPlateSvg(),
  "left-half-bottom-plate.dxf": makeBottomDxf(),
  "right-half-plate.svg": makePlateSvg("right"),
  "right-half-plate.dxf": makeDxf("right"),
  "right-half-bottom-plate.svg": makeBottomPlateSvg("right"),
  "right-half-bottom-plate.dxf": makeBottomDxf("right"),
  "choc-v1-acrylic-fit-coupon.svg": makeAcrylicFitCouponSvg(),
  "choc-v1-acrylic-fit-coupon.dxf": makeAcrylicFitCouponDxf(),
  "key-positions.json": `${makePositionsJson()}\n`
};

for (const [fileName, contents] of Object.entries(artifacts)) {
  fs.writeFileSync(path.join(outputDirectory, fileName), contents);
}

console.log(
  `Generated ${Object.keys(artifacts).length} files for ${leftKeys.length * 2} press inputs in ${path.relative(process.cwd(), outputDirectory) || outputDirectory}`
);
