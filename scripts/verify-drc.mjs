#!/usr/bin/env node
/** Run KiCad DRC and reject everything except reviewed reversible-route stubs. */

import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const board = 'arc58-reversible.kicad_pcb';
const boardPath = join(root, 'hardware', 'kicad', board);
const reportDir = mkdtempSync(join(tmpdir(), 'arc58-drc-'));
const report = join(reportDir, `${board}.json`);
const reviewedWarnings = new Map([
  ['track_dangling', 24],
  ['via_dangling', 3],
]);

function fail(message) {
  throw new Error(`FAIL: ${message}`);
}

try {
  try {
    execFileSync(
      'kicad-cli',
      ['pcb', 'drc', '--format', 'json', '--output', report, boardPath],
      { stdio: 'pipe' },
    );
  } catch (error) {
    // KiCad exits nonzero for warnings too; parse its report below.
    if (!error.status && !error.signal) throw error;
  }

  const result = JSON.parse(readFileSync(report, 'utf8'));
  if (result.unconnected_items.length) {
    fail(`${result.unconnected_items.length} unrouted connections`);
  }

  const counts = new Map();
  for (const violation of result.violations) {
    if (!reviewedWarnings.has(violation.type) || violation.severity !== 'warning') {
      const items = violation.items.map((item) => item.description).join(' | ');
      fail(`DRC ${violation.type}: ${violation.description}; ${items}`);
    }
    counts.set(violation.type, (counts.get(violation.type) ?? 0) + 1);
  }
  for (const [type, expected] of reviewedWarnings) {
    const actual = counts.get(type) ?? 0;
    if (actual !== expected) {
      fail(`reviewed-warning baseline changed for ${type}: expected ${expected}, found ${actual}`);
    }
  }

  console.log(
    `PASS: ${board} — zero unrouted/electrical/clearance/mask/silkscreen violations; ` +
    '27 reviewed reversible-route stub warnings match the pinned baseline.',
  );
} finally {
  rmSync(reportDir, { recursive: true, force: true });
}
