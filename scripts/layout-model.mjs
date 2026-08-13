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

export function roundedRectanglePoints(
  center,
  width,
  height,
  radius,
  stepsPerCorner = 8
) {
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

function pointInPolygon(point, polygon) {
  let inside = false;
  for (let index = 0; index < polygon.length; index += 1) {
    const start = polygon[index];
    const end = polygon[(index + 1) % polygon.length];
    if (
      (start.y > point.y) !== (end.y > point.y) &&
      point.x <
        ((end.x - start.x) * (point.y - start.y)) / (end.y - start.y) +
          start.x
    ) {
      inside = !inside;
    }
  }
  return inside;
}

function segmentIntersection(firstStart, firstEnd, secondStart, secondEnd) {
  const first = {
    x: firstEnd.x - firstStart.x,
    y: firstEnd.y - firstStart.y
  };
  const second = {
    x: secondEnd.x - secondStart.x,
    y: secondEnd.y - secondStart.y
  };
  const denominator = first.x * second.y - first.y * second.x;
  if (Math.abs(denominator) < 1e-12) return null;

  const offset = {
    x: secondStart.x - firstStart.x,
    y: secondStart.y - firstStart.y
  };
  const firstAmount =
    (offset.x * second.y - offset.y * second.x) / denominator;
  const secondAmount =
    (offset.x * first.y - offset.y * first.x) / denominator;
  const epsilon = 1e-9;
  if (
    firstAmount <= epsilon ||
    firstAmount >= 1 - epsilon ||
    secondAmount <= epsilon ||
    secondAmount >= 1 - epsilon
  ) {
    return null;
  }
  return {
    firstAmount,
    secondAmount,
    point: {
      x: firstStart.x + firstAmount * first.x,
      y: firstStart.y + firstAmount * first.y
    }
  };
}

function splitPolygonSegments(polygon, other) {
  const segments = [];
  for (let index = 0; index < polygon.length; index += 1) {
    const start = polygon[index];
    const end = polygon[(index + 1) % polygon.length];
    const intersections = [];
    for (let otherIndex = 0; otherIndex < other.length; otherIndex += 1) {
      const intersection = segmentIntersection(
        start,
        end,
        other[otherIndex],
        other[(otherIndex + 1) % other.length]
      );
      if (intersection !== null) intersections.push(intersection);
    }
    intersections.sort((a, b) => a.firstAmount - b.firstAmount);
    const points = [start, ...intersections.map((item) => item.point), end];
    for (let pointIndex = 0; pointIndex < points.length - 1; pointIndex += 1) {
      const segmentStart = points[pointIndex];
      const segmentEnd = points[pointIndex + 1];
      segments.push({
        start: segmentStart,
        end: segmentEnd,
        midpoint: {
          x: (segmentStart.x + segmentEnd.x) / 2,
          y: (segmentStart.y + segmentEnd.y) / 2
        }
      });
    }
  }
  return segments;
}

function samePoint(first, second, tolerance = 1e-7) {
  return Math.hypot(first.x - second.x, first.y - second.y) <= tolerance;
}

function assembleSingleLoop(segments) {
  if (segments.length === 0) throw new Error("No boundary segments remain");
  const remaining = [...segments];
  const first = remaining.shift();
  const result = [first.start, first.end];

  while (remaining.length > 0) {
    const current = result.at(-1);
    const nextIndex = remaining.findIndex(
      (segment) =>
        samePoint(segment.start, current) || samePoint(segment.end, current)
    );
    if (nextIndex === -1) {
      throw new Error("Boolean boundary contains a disconnected contour");
    }
    const [next] = remaining.splice(nextIndex, 1);
    result.push(
      samePoint(next.start, current) ? next.end : next.start
    );
  }

  if (!samePoint(result[0], result.at(-1))) {
    throw new Error("Boolean boundary is not closed");
  }
  result.pop();
  return result;
}

function combineBoundaries(first, second, operation) {
  const firstSegments = splitPolygonSegments(first, second);
  const secondSegments = splitPolygonSegments(second, first);
  const kept = [];
  if (operation === "union") {
    kept.push(
      ...firstSegments.filter((segment) => !pointInPolygon(segment.midpoint, second)),
      ...secondSegments.filter((segment) => !pointInPolygon(segment.midpoint, first))
    );
  } else if (operation === "difference") {
    kept.push(
      ...firstSegments.filter((segment) => !pointInPolygon(segment.midpoint, second)),
      ...secondSegments.filter((segment) => pointInPolygon(segment.midpoint, first))
    );
  } else {
    throw new Error(`Unsupported polygon operation: ${operation}`);
  }
  return assembleSingleLoop(kept);
}

export function mergedTopPlateOutline(
  outline,
  electronicsWindow,
  trrsSlot
) {
  const electronics = roundedRectanglePoints(
    { x: electronicsWindow.centerX, y: electronicsWindow.centerY },
    electronicsWindow.width,
    electronicsWindow.height,
    electronicsWindow.cornerRadius
  );
  const slot = roundedRectanglePoints(
    { x: trrsSlot.centerX, y: trrsSlot.centerY },
    trrsSlot.width,
    trrsSlot.height,
    trrsSlot.cornerRadius
  );
  const combinedOpening = combineBoundaries(electronics, slot, "union");
  return combineBoundaries(outline, combinedOpening, "difference");
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
