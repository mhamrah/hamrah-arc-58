import fs from "node:fs";

export function readConfig(configUrl = new URL("../layout.config.json", import.meta.url)) {
  return JSON.parse(fs.readFileSync(configUrl, "utf8"));
}

export function rotatePoint(point, center, angleDeg) {
  const angle = (angleDeg * Math.PI) / 180;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const dx = point.x - center.x;
  const dy = point.y - center.y;
  return {
    x: center.x + dx * cos - dy * sin,
    y: center.y + dx * sin + dy * cos
  };
}

export function rectangleCorners(key, width, height) {
  const halfWidth = width / 2;
  const halfHeight = height / 2;
  const corners = [
    { x: key.x - halfWidth, y: key.y - halfHeight },
    { x: key.x + halfWidth, y: key.y - halfHeight },
    { x: key.x + halfWidth, y: key.y + halfHeight },
    { x: key.x - halfWidth, y: key.y + halfHeight }
  ];
  return corners.map((point) => rotatePoint(point, key, key.rotation));
}

export function componentEnvelope(component, config) {
  if (component.group === "encoder") {
    return rectangleCorners(
      component,
      config.encoder.knobDiameter,
      config.encoder.knobDiameter
    );
  }
  return rectangleCorners(
    component,
    config.switch.keycapWidth,
    config.switch.keycapHeight
  );
}

export function buildHalf(config) {
  const { matrix, switch: switchConfig, encoder, thumbArc } = config;
  const keys = [];

  for (let column = 0; column < matrix.columns; column += 1) {
    for (let row = 0; row < matrix.rows; row += 1) {
      keys.push({
        id: `c${column + 1}r${row + 1}`,
        group: "matrix",
        column,
        row,
        x: column * switchConfig.pitchX,
        y: matrix.columnStagger[column] + row * switchConfig.pitchY,
        rotation: 0
      });
    }
  }

  if (encoder.enabled) {
    const alignedColumn = encoder.alignWithColumn;
    if (
      encoder.horizontalPlacement !==
      "equal-clearance-between-c6-and-inner-edge"
    ) {
      throw new Error(
        `Unsupported encoder placement: ${encoder.horizontalPlacement}`
      );
    }
    const y =
      matrix.columnStagger[alignedColumn] +
      encoder.row * switchConfig.pitchY;
    const innerEdgeX = Math.max(...outlineCrossingsAtY(config.mechanical, y));
    const columnEdgeX =
      (matrix.columns - 1) * switchConfig.pitchX +
      switchConfig.keycapWidth / 2;
    keys.push({
      id: "encoder",
      group: "encoder",
      x: (columnEdgeX + innerEdgeX) / 2,
      y,
      rotation: 0
    });
  }

  const [startColumnA, startColumnB] = thumbArc.startBetweenColumns;
  const startX =
    ((startColumnA + startColumnB) / 2) * switchConfig.pitchX -
    thumbArc.startOffsetTowardOuterEdge;
  const startY =
    Math.max(
      matrix.columnStagger[startColumnA] +
        (matrix.rows - 1) * switchConfig.pitchY,
      matrix.columnStagger[startColumnB] +
        (matrix.rows - 1) * switchConfig.pitchY
    ) + thumbArc.dropFromLowerColumnKey;

  let thumbX = startX;
  let thumbY = startY;
  for (let index = 0; index < thumbArc.count; index += 1) {
    keys.push({
      id: `thumb${index + 1}`,
      group: "thumb",
      index,
      x: thumbX,
      y: thumbY,
      rotation: thumbArc.keyRotations[index]
    });

    const angle = thumbArc.segmentAngles[index];
    if (angle !== undefined) {
      const radians = (angle * Math.PI) / 180;
      thumbX += thumbArc.step * Math.cos(radians);
      thumbY += thumbArc.step * Math.sin(radians);
    }
  }

  return keys;
}

function cross(origin, a, b) {
  return (
    (a.x - origin.x) * (b.y - origin.y) -
    (a.y - origin.y) * (b.x - origin.x)
  );
}

export function convexHull(points) {
  const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y);
  if (sorted.length <= 1) return sorted;

  const lower = [];
  for (const point of sorted) {
    while (
      lower.length >= 2 &&
      cross(lower.at(-2), lower.at(-1), point) <= 0
    ) {
      lower.pop();
    }
    lower.push(point);
  }

  const upper = [];
  for (const point of sorted.reverse()) {
    while (
      upper.length >= 2 &&
      cross(upper.at(-2), upper.at(-1), point) <= 0
    ) {
      upper.pop();
    }
    upper.push(point);
  }

  lower.pop();
  upper.pop();
  return lower.concat(upper);
}

export function plateOutline(keys, config) {
  return convexHull(
    keys.flatMap((key) =>
      rectangleCorners(
        key,
        (key.group === "encoder"
          ? config.encoder.knobDiameter
          : config.switch.keycapWidth) + config.preview.plateMargin * 2,
        (key.group === "encoder"
          ? config.encoder.knobDiameter
          : config.switch.keycapHeight) + config.preview.plateMargin * 2
      )
    )
  );
}

export function closedCatmullRomSegments(points, tension = 1) {
  if (points.length < 3) {
    throw new Error("A closed curve needs at least three anchors");
  }
  return points.map((start, index) => {
    const previous = points[(index - 1 + points.length) % points.length];
    const end = points[(index + 1) % points.length];
    const following = points[(index + 2) % points.length];
    return {
      start,
      control1: {
        x: start.x + ((end.x - previous.x) * tension) / 6,
        y: start.y + ((end.y - previous.y) * tension) / 6
      },
      control2: {
        x: end.x - ((following.x - start.x) * tension) / 6,
        y: end.y - ((following.y - start.y) * tension) / 6
      },
      end
    };
  });
}

export function closedOutlineSegments(mechanical) {
  const points = mechanical.boardOutline;
  if (mechanical.outlineCurveMode !== "explicit-bezier") {
    return closedCatmullRomSegments(points, mechanical.outlineCurveTension);
  }
  if (
    points.length < 3 ||
    points.some((point) => point.controlIn === undefined || point.controlOut === undefined)
  ) {
    throw new Error("An explicit Bezier outline needs at least three anchors with control handles");
  }
  return points.map((start, index) => {
    const end = points[(index + 1) % points.length];
    return {
      start: { x: start.x, y: start.y },
      control1: { x: start.controlOut.x, y: start.controlOut.y },
      control2: { x: end.controlIn.x, y: end.controlIn.y },
      end: { x: end.x, y: end.y }
    };
  });
}

export function sampleCubicBezier(segment, steps = 24) {
  const points = [];
  for (let index = 0; index < steps; index += 1) {
    const t = index / steps;
    const u = 1 - t;
    points.push({
      x:
        u ** 3 * segment.start.x +
        3 * u ** 2 * t * segment.control1.x +
        3 * u * t ** 2 * segment.control2.x +
        t ** 3 * segment.end.x,
      y:
        u ** 3 * segment.start.y +
        3 * u ** 2 * t * segment.control1.y +
        3 * u * t ** 2 * segment.control2.y +
        t ** 3 * segment.end.y
    });
  }
  return points;
}

export function sampleClosedCurve(segments, steps = 24) {
  return segments.flatMap((segment) => sampleCubicBezier(segment, steps));
}

export function outlineCrossingsAtY(mechanical, y, steps = 2048) {
  const outline = sampleClosedCurve(closedOutlineSegments(mechanical), steps);
  const crossings = [];
  for (let index = 0; index < outline.length; index += 1) {
    const start = outline[index];
    const end = outline[(index + 1) % outline.length];
    if (
      (start.y <= y && end.y > y) ||
      (end.y <= y && start.y > y)
    ) {
      const amount = (y - start.y) / (end.y - start.y);
      crossings.push(start.x + amount * (end.x - start.x));
    }
  }
  if (crossings.length < 2) {
    throw new Error(`Board outline does not cross y=${y} twice`);
  }
  return crossings;
}

export function boundsForPoints(points) {
  return points.reduce(
    (bounds, point) => ({
      minX: Math.min(bounds.minX, point.x),
      minY: Math.min(bounds.minY, point.y),
      maxX: Math.max(bounds.maxX, point.x),
      maxY: Math.max(bounds.maxY, point.y)
    }),
    { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity }
  );
}

export function mirrorKey(key, axisX) {
  return {
    ...key,
    x: axisX - key.x,
    rotation: -key.rotation
  };
}

export function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}
