import assert from "node:assert/strict";
import test from "node:test";
import {
  buildHalf,
  closedOutlineSegments,
  componentEnvelope,
  distance,
  mirrorKey,
  outlineCrossingsAtY,
  readConfig,
  rectangleCorners,
  sampleClosedCurve
} from "../scripts/layout-model.mjs";

const config = readConfig();
const keys = buildHalf(config);
const matrixKeys = keys.filter((key) => key.group === "matrix");
const thumbKeys = keys.filter((key) => key.group === "thumb");

function pointToSegment(point, a, b) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const t = Math.max(
    0,
    Math.min(
      1,
      ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy)
    )
  );
  return Math.hypot(point.x - (a.x + t * dx), point.y - (a.y + t * dy));
}

function projection(polygon, axis) {
  const values = polygon.map((point) => point.x * axis.x + point.y * axis.y);
  return { min: Math.min(...values), max: Math.max(...values) };
}

function polygonsOverlap(polygonA, polygonB) {
  for (const polygon of [polygonA, polygonB]) {
    for (let index = 0; index < polygon.length; index += 1) {
      const next = (index + 1) % polygon.length;
      const edge = {
        x: polygon[next].x - polygon[index].x,
        y: polygon[next].y - polygon[index].y
      };
      const axis = { x: -edge.y, y: edge.x };
      const a = projection(polygonA, axis);
      const b = projection(polygonB, axis);
      if (a.max <= b.min || b.max <= a.min) return false;
    }
  }
  return true;
}

function polygonGap(a, b) {
  if (polygonsOverlap(a, b)) return 0;
  let gap = Infinity;
  for (const [points, edges] of [[a, b], [b, a]]) {
    for (const point of points) {
      for (let index = 0; index < edges.length; index += 1) {
        gap = Math.min(
          gap,
          pointToSegment(point, edges[index], edges[(index + 1) % edges.length])
        );
      }
    }
  }
  return gap;
}

test("design is named for its 58 press inputs", () => {
  assert.equal(config.name, "Hamrah Arc 58");
  assert.equal(config.revision, "Beta");
  assert.equal(keys.length * 2, 58);
});

test("layout keeps 29 press inputs per half", () => {
  assert.equal(matrixKeys.length, 24);
  assert.equal(keys.filter((key) => key.group === "encoder").length, 1);
  assert.equal(thumbKeys.length, 4);
  assert.equal(keys.length * 2, 58);
});

test("a clickable encoder is mirrored onto both halves", () => {
  const encoder = keys.find((key) => key.group === "encoder");
  const axisX = 57.15;
  const mirrored = mirrorKey(encoder, axisX);
  assert.equal(config.encoder.click, true);
  assert.equal(config.encoder.partNumber, "EC11E15244G1");
  assert.equal(
    config.encoder.sofleFootprint,
    "SofleKeyboard-footprint:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm-keebio_modified"
  );
  assert.equal(config.encoder.plateHoleDiameter, 7.2);
  assert.equal(encoder.y, mirrored.y);
  assert.equal(encoder.rotation, -mirrored.rotation);
});

test("encoder has equal empty space to C6 and the curved inner edge", () => {
  const encoder = keys.find((key) => key.group === "encoder");
  const nearestKey = keys.find((key) => key.id === "c6r4");
  const innerEdgeX = Math.max(
    ...outlineCrossingsAtY(config.mechanical, encoder.y)
  );
  const knobRadius = config.encoder.knobDiameter / 2;
  const capEdgeX = nearestKey.x + config.switch.keycapWidth / 2;
  const capGap = encoder.x - knobRadius - capEdgeX;
  const boardGap = innerEdgeX - encoder.x - knobRadius;
  const sampledOutline = sampleClosedCurve(
    closedOutlineSegments(config.mechanical),
    2048
  );
  const curvedBoardGap =
    Math.min(
      ...sampledOutline.map((point, index) =>
        pointToSegment(
          encoder,
          point,
          sampledOutline[(index + 1) % sampledOutline.length]
        )
      )
    ) - knobRadius;

  assert.equal(
    config.encoder.horizontalPlacement,
    "equal-clearance-between-c6-and-inner-edge"
  );
  assert.ok(Math.abs(capGap - boardGap) < 0.001);
  assert.ok(Math.abs(capGap - curvedBoardGap) < 0.01);
  assert.ok(capGap > 9);
});

test("first thumb key starts one millimetre toward the outer edge", () => {
  const [columnA, columnB] = config.thumbArc.startBetweenColumns;
  const expectedX =
    ((columnA + columnB) / 2) * config.switch.pitchX -
    config.thumbArc.startOffsetTowardOuterEdge;
  assert.equal(config.thumbArc.startOffsetTowardOuterEdge, 1);
  assert.equal(thumbKeys[0].x, expectedX);
});

test("matrix matches the mirrored left-half Sofle Choc spacing and stagger", () => {
  assert.equal(config.switch.pitchX, 19.05);
  assert.equal(config.switch.pitchY, 19.05);
  assert.deepEqual(config.matrix.columnStagger, [7.4, 7.4, 2.5, 0, 2.5, 5]);
  assert.equal(Math.min(...config.matrix.columnStagger), config.matrix.columnStagger[3]);
});

test("thumb keys form a descending inward arc", () => {
  for (let index = 1; index < thumbKeys.length; index += 1) {
    assert.ok(thumbKeys[index].x > thumbKeys[index - 1].x);
    assert.ok(thumbKeys[index].y > thumbKeys[index - 1].y);
    assert.ok(thumbKeys[index].rotation > thumbKeys[index - 1].rotation);
    assert.ok(
      Math.abs(distance(thumbKeys[index], thumbKeys[index - 1]) - config.thumbArc.step) <
        1e-9
    );
  }
});

test("keycaps and encoder knob do not overlap", () => {
  const polygons = keys.map((key) => ({
    id: key.id,
    corners: componentEnvelope(key, config)
  }));

  for (let a = 0; a < polygons.length; a += 1) {
    for (let b = a + 1; b < polygons.length; b += 1) {
      assert.ok(
        !polygonsOverlap(polygons[a].corners, polygons[b].corners),
        `${polygons[a].id} overlaps ${polygons[b].id}`
      );
    }
  }
});

test("thumb arc clears the conservative 18 mm keycap envelope", () => {
  const envelope = config.switch.keycapClearanceEnvelope;
  assert.deepEqual(envelope, { width: 18, height: 18, minimumGap: 0.5 });
  assert.equal(config.thumbArc.step, 21.25);

  for (let index = 0; index < thumbKeys.length - 1; index += 1) {
    const first = rectangleCorners(thumbKeys[index], envelope.width, envelope.height);
    const second = rectangleCorners(
      thumbKeys[index + 1],
      envelope.width,
      envelope.height
    );
    assert.ok(
      polygonGap(first, second) >= envelope.minimumGap,
      `T${index + 1}-T${index + 2} keycap gap is below ${envelope.minimumGap} mm`
    );
  }
});

test("thumb arc leaves over two millimetres between specified keycaps", () => {
  for (let index = 0; index < thumbKeys.length - 1; index += 1) {
    const first = rectangleCorners(
      thumbKeys[index],
      config.switch.keycapWidth,
      config.switch.keycapHeight
    );
    const second = rectangleCorners(
      thumbKeys[index + 1],
      config.switch.keycapWidth,
      config.switch.keycapHeight
    );
    assert.ok(
      polygonGap(first, second) >= 2.25,
      `T${index + 1}-T${index + 2} specified-keycap gap is below 2.25 mm`
    );
  }
});

test("T1 preserves matrix clearance after the outward shift", () => {
  const thumbOne = keys.find((key) => key.id === "thumb1");
  const c5r4 = keys.find((key) => key.id === "c5r4");
  const c6r4 = keys.find((key) => key.id === "c6r4");
  assert.equal(config.thumbArc.dropFromLowerColumnKey, 19);

  const corners = (key) =>
    rectangleCorners(key, config.switch.keycapWidth, config.switch.keycapHeight);
  assert.ok(polygonGap(corners(thumbOne), corners(c5r4)) >= 2.5);
  assert.ok(polygonGap(corners(thumbOne), corners(c6r4)) >= 2.5);
});

test("Choc v1 plate cutout remains 14 mm square", () => {
  assert.equal(config.switch.plateCutout, 14);
  assert.equal(config.switch.keycapWidth, 16.5);
  assert.equal(config.switch.keycapHeight, 16.5);
});

test("per-key RGB specifies one routed aperture for every LED", () => {
  assert.equal(config.rgb.partNumber, "SK6812MINI-E");
  assert.equal(config.rgb.ledsPerHalf, 28);
  assert.equal(config.rgb.ledsPerHalf, keys.length - 1);
  assert.equal(config.rgb.apertureWidth, 3.6);
  assert.equal(config.rgb.apertureHeight, 3.1);
});

test("TRRS jack and ten-millimetre plug envelope exit through the inner edge", () => {
  const trrs = config.trrs;
  const transform = config.manufacturing.pcbTransform;
  assert.equal(trrs.partNumber, "MJ-4PP-9");
  assert.equal(trrs.pcbRotation, 0);
  assert.ok(Math.abs(transform.originX - trrs.layoutCenter.x - trrs.pcbCenter.x) < 1e-9);
  assert.ok(Math.abs(transform.originY + trrs.layoutCenter.y - trrs.pcbCenter.y) < 1e-9);

  const outline = sampleClosedCurve(closedOutlineSegments(config.mechanical), 500);
  const mouthX = trrs.layoutCenter.x + trrs.mouthOffset;
  const crossings = [];
  for (let index = 0; index < outline.length; index += 1) {
    const start = outline[index];
    const end = outline[(index + 1) % outline.length];
    if ((start.y <= trrs.layoutCenter.y && end.y > trrs.layoutCenter.y) ||
        (end.y <= trrs.layoutCenter.y && start.y > trrs.layoutCenter.y)) {
      const amount = (trrs.layoutCenter.y - start.y) / (end.y - start.y);
      crossings.push(start.x + amount * (end.x - start.x));
    }
  }
  const innerEdge = Math.max(...crossings);
  assert.ok(mouthX >= innerEdge, "TRRS mouth does not reach the PCB edge");
  assert.ok(mouthX - innerEdge <= 1, "TRRS mouth overhang exceeds one millimetre");

  const window = config.mechanical.acrylic.electronicsWindow;
  const slot = trrs.plateSlot;
  assert.ok(slot.centerX - slot.width / 2 <= window.centerX + window.width / 2);
  assert.ok(
    slot.centerX + slot.width / 2 >= innerEdge + config.mechanical.cncCase.outerWall,
    "TRRS slot does not pass through the CNC rim"
  );
  assert.ok(slot.height >= trrs.plugClearanceDiameter);

  const plugBottom =
    config.mechanical.cncCase.pcbUndersideHeight +
    1.6 +
    trrs.portCenterHeight -
    trrs.plugClearanceDiameter / 2;
  assert.ok(trrs.caseNotchBottom <= plugBottom);
  assert.ok(trrs.caseNotchBottom >= config.mechanical.cncCase.floorThickness);
});

test("the shared mechanical design has a smooth outline and six clear M2 fasteners", () => {
  assert.equal(config.mechanical.mountingHoleDiameter, 2.2);
  assert.equal(config.mechanical.mountingHoles.length, 6);
  assert.ok(config.mechanical.boardOutline.length >= 12);
  assert.equal(config.mechanical.outlineCurveMode, "explicit-bezier");
  assert.ok(
    config.mechanical.boardOutline.every(
      (point) => point.controlIn !== undefined && point.controlOut !== undefined
    )
  );
  const segments = closedOutlineSegments(config.mechanical);
  assert.equal(segments.length, config.mechanical.boardOutline.length);
  assert.equal(sampleClosedCurve(segments).length, segments.length * 24);
  for (let index = 0; index < segments.length; index += 1) {
    const next = segments[(index + 1) % segments.length];
    assert.deepEqual(segments[index].end, next.start);
    const incoming = {
      x: segments[index].end.x - segments[index].control2.x,
      y: segments[index].end.y - segments[index].control2.y
    };
    const outgoing = {
      x: next.control1.x - next.start.x,
      y: next.control1.y - next.start.y
    };
    const cross = incoming.x * outgoing.y - incoming.y * outgoing.x;
    const dot = incoming.x * outgoing.x + incoming.y * outgoing.y;
    assert.ok(Math.abs(cross) < 0.01, `outline join ${index + 1} is not tangent-continuous`);
    assert.ok(dot > 0, `outline join ${index + 1} reverses direction`);
  }
  for (const hole of config.mechanical.mountingHoles) {
    const nearest = Math.min(...keys.map((key) => distance(hole, key)));
    assert.ok(nearest > 13, `mounting hole at ${hole.x}, ${hole.y} is too near a key`);
  }
  const encoder = keys.find((key) => key.group === "encoder");
  const h4 = config.mechanical.mountingHoles[3];
  const encoderBossGap =
    distance(encoder, h4) -
    config.encoder.knobDiameter / 2 -
    config.mechanical.cncCase.bossDiameter / 2;
  const sampledOutline = sampleClosedCurve(
    closedOutlineSegments(config.mechanical),
    2048
  );
  const h4OutlineGap =
    Math.min(
      ...sampledOutline.map((point, index) =>
        pointToSegment(
          h4,
          point,
          sampledOutline[(index + 1) % sampledOutline.length]
        )
      )
    ) - config.mechanical.cncCase.bossDiameter / 2;
  assert.ok(encoderBossGap > 3.5, `H4 boss gap is only ${encoderBossGap} mm`);
  assert.ok(h4OutlineGap > 3, `H4 outline gap is only ${h4OutlineGap} mm`);
});

test("acrylic plates use prototype-safe dimensions and preserve the electronics bay", () => {
  const acrylic = config.mechanical.acrylic;
  assert.equal(acrylic.material, "cast acrylic");
  assert.equal(acrylic.topThickness, 1.5);
  assert.equal(acrylic.bottomThickness, 3);
  assert.equal(acrylic.mountingHoleDiameter, 2.4);
  assert.equal(acrylic.resetAccessDiameter, 4.5);
  assert.ok(acrylic.fitCouponCutouts.includes(config.switch.plateCutout));

  const window = acrylic.electronicsWindow;
  const left = window.centerX - window.width / 2;
  const right = window.centerX + window.width / 2;
  const top = window.centerY - window.height / 2;
  const bottom = window.centerY + window.height / 2;
  let nearestSwitchGap = Infinity;
  for (const key of keys.filter((candidate) => candidate.group !== "encoder")) {
    const corners = rectangleCorners(key, config.switch.plateCutout, config.switch.plateCutout);
    const keyLeft = Math.min(...corners.map((point) => point.x));
    const keyRight = Math.max(...corners.map((point) => point.x));
    const keyTop = Math.min(...corners.map((point) => point.y));
    const keyBottom = Math.max(...corners.map((point) => point.y));
    const gapX = Math.max(left - keyRight, keyLeft - right, 0);
    const gapY = Math.max(top - keyBottom, keyTop - bottom, 0);
    nearestSwitchGap = Math.min(nearestSwitchGap, Math.hypot(gapX, gapY));
  }
  assert.ok(nearestSwitchGap >= 2, `electronics window ligament is only ${nearestSwitchGap} mm`);

  for (const hole of config.mechanical.mountingHoles) {
    const gapX = Math.max(left - hole.x, hole.x - right, 0);
    const gapY = Math.max(top - hole.y, hole.y - bottom, 0);
    assert.ok(
      Math.hypot(gapX, gapY) > acrylic.mountingHoleDiameter / 2 + 1.5,
      `electronics window is too close to mounting hole at ${hole.x}, ${hole.y}`
    );
  }
});

test("CNC case dimensions satisfy the conservative machining envelope", () => {
  const enclosure = config.mechanical.cncCase;
  assert.equal(enclosure.material, "6061-T6 aluminum");
  assert.ok(enclosure.outerWall - enclosure.pcbPerimeterClearance >= 2);
  assert.ok(enclosure.floorThickness >= 2.5);
  assert.ok(enclosure.pcbUndersideHeight - enclosure.floorThickness >= 3.2);
  assert.ok(enclosure.bossDiameter >= 6);
  assert.equal(enclosure.tapDrillDiameter, 1.6);
  assert.equal(enclosure.thread, "M2 x 0.4");
  assert.ok(enclosure.threadDepth >= 3);
  assert.equal(enclosure.topPlateThickness, 1.5);
  assert.ok(enclosure.pcbToPlateGap >= 2);
});
