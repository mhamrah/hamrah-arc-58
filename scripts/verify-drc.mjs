#!/usr/bin/env node
/** Run KiCad DRC and reject everything except reviewed reversible-route stubs. */

import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const board = 'arc58-reversible.kicad_pcb';
const boardPath = join(root, 'hardware', 'kicad', board);
const reportDir = mkdtempSync(join(tmpdir(), 'arc58-drc-'));
const report = join(reportDir, `${board}.json`);
const reviewedWarnings = new Map();

function fail(message) {
  throw new Error(`FAIL: ${message}`);
}

try {
  for (let attempt = 1; attempt <= 5 && !existsSync(report); attempt += 1) {
    try {
      execFileSync(
        'kicad-cli',
        ['pcb', 'drc', '--format', 'json', '--output', report, boardPath],
        { stdio: 'pipe' },
      );
    } catch (error) {
      // KiCad exits nonzero for warnings too. It also intermittently crashes
      // on macOS before writing JSON, so retry only when no report exists.
      if (!error.status && !error.signal) throw error;
    }
  }
  if (!existsSync(report)) {
    fail('KiCad did not produce a DRC report after five attempts');
  }

  const result = JSON.parse(readFileSync(report, 'utf8'));
  if (result.unconnected_items.length) {
    fail(`${result.unconnected_items.length} unrouted connections`);
  }

  const counts = new Map();
  const unexpected = [];
  for (const violation of result.violations) {
    if (!reviewedWarnings.has(violation.type) || violation.severity !== 'warning') {
      const items = violation.items.map((item) => item.description).join(' | ');
      unexpected.push(`DRC ${violation.type}: ${violation.description}; ${items}`);
      continue;
    }
    counts.set(violation.type, (counts.get(violation.type) ?? 0) + 1);
  }
  if (unexpected.length) fail(unexpected.join('\n'));
  for (const [type, expected] of reviewedWarnings) {
    const actual = counts.get(type) ?? 0;
    if (actual !== expected) {
      fail(`reviewed-warning baseline changed for ${type}: expected ${expected}, found ${actual}`);
    }
  }

  console.log(
    `PASS: ${board} — zero unrouted/electrical/clearance/mask/silkscreen violations; ` +
    'zero KiCad DRC warnings.',
  );
} finally {
  rmSync(reportDir, { recursive: true, force: true });
}
