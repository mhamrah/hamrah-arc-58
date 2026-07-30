import assert from "node:assert/strict";
import test from "node:test";
import {
  buildHalf,
  componentEnvelope,
  distance,
  mirrorKey,
  readConfig,
  rectangleCorners
} from "../scripts/layout-model.mjs";

const config = readConfig();
const keys = buildHalf(config);
const matrixKeys = keys.filter((key) => key.group === "matrix");
const thumbKeys = keys.filter((key) => key.group === "thumb");

test("design is named for its 58 press inputs", () => {
  assert.equal(config.name, "Hamrah Arc 58");
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

test("first thumb key starts midway between the two innermost columns", () => {
  const [columnA, columnB] = config.thumbArc.startBetweenColumns;
  const expectedX =
    ((columnA + columnB) / 2) * config.switch.pitchX;
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

  function projection(polygon, axis) {
    const values = polygon.map((point) => point.x * axis.x + point.y * axis.y);
    return { min: Math.min(...values), max: Math.max(...values) };
  }

  function overlaps(polygonA, polygonB) {
    const polygonsToCheck = [polygonA, polygonB];
    for (const polygon of polygonsToCheck) {
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

  for (let a = 0; a < polygons.length; a += 1) {
    for (let b = a + 1; b < polygons.length; b += 1) {
      assert.ok(
        !overlaps(polygons[a].corners, polygons[b].corners),
        `${polygons[a].id} overlaps ${polygons[b].id}`
      );
    }
  }
});

test("T1 has the requested extra millimetre of matrix clearance", () => {
  const thumbOne = keys.find((key) => key.id === "thumb1");
  const c5r4 = keys.find((key) => key.id === "c5r4");
  const c6r4 = keys.find((key) => key.id === "c6r4");
  assert.equal(config.thumbArc.dropFromLowerColumnKey, 19);

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

  function polygonGap(a, b) {
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

  const corners = (key) =>
    rectangleCorners(key, config.switch.keycapWidth, config.switch.keycapHeight);
  assert.ok(Math.abs(polygonGap(corners(thumbOne), corners(c5r4)) - 3.606) < 0.001);
  assert.ok(Math.abs(polygonGap(corners(thumbOne), corners(c6r4)) - 2.471) < 0.001);
});

test("Choc v1 plate cutout remains 14 mm square", () => {
  assert.equal(config.switch.plateCutout, 14);
});
