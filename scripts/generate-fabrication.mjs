#!/usr/bin/env node
/** Generate and sanity-check the one reversible PCB fabrication ZIP. */

import { execFileSync } from 'node:child_process';
import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const board = join(root, 'hardware', 'kicad', 'arc58-reversible.kicad_pcb');
const layout = JSON.parse(readFileSync(join(root, 'layout.config.json'), 'utf8'));
const revisionSlug = layout.revision.toLowerCase();
const packageName = `arc58-reversible-pcb-rev-${revisionSlug}`;
const tempRoot = mkdtempSync(join(tmpdir(), 'arc58-fab-'));
const staging = join(tempRoot, packageName);
const output = join(root, 'output', 'fabrication', `${packageName}.zip`);

const expected = [
  'README.md',
  'arc58-reversible-F_Cu.gtl',
  'arc58-reversible-B_Cu.gbl',
  'arc58-reversible-F_Mask.gts',
  'arc58-reversible-B_Mask.gbs',
  'arc58-reversible-F_Silkscreen.gto',
  'arc58-reversible-B_Silkscreen.gbo',
  'arc58-reversible-Edge_Cuts.gm1',
  'arc58-reversible-PTH.drl',
  'arc58-reversible-NPTH.drl',
  'arc58-reversible-job.gbrjob',
  'arc58-reversible.d356',
  'arc58-reversible-drill-report.txt',
  'arc58-reversible-stats.txt',
];

function run(command, args) {
  execFileSync(command, args, { cwd: root, stdio: 'inherit' });
}

try {
  mkdirSync(staging, { recursive: true });
  run(process.execPath, [join(root, 'scripts', 'verify-drc.mjs')]);
  run('kicad-cli', [
    'pcb', 'export', 'gerbers',
    '--layers', 'F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts',
    '--subtract-soldermask', '--precision', '6', '--output', staging, board,
  ]);
  run('kicad-cli', [
    'pcb', 'export', 'drill', '--output', staging, '--format', 'excellon',
    '--excellon-units', 'mm', '--excellon-separate-th', '--generate-report',
    '--report-path', join(staging, 'arc58-reversible-drill-report.txt'), board,
  ]);
  run('kicad-cli', [
    'pcb', 'export', 'ipcd356', '--output',
    join(staging, 'arc58-reversible.d356'), board,
  ]);
  run('kicad-cli', [
    'pcb', 'export', 'stats', '--output',
    join(staging, 'arc58-reversible-stats.txt'), board,
  ]);
  copyFileSync(join(root, 'hardware', 'FABRICATION-README.md'), join(staging, 'README.md'));

  for (const name of expected) {
    const path = join(staging, name);
    if (statSync(path).size === 0) throw new Error(`empty fabrication file: ${name}`);
  }
  for (const name of expected.filter((name) => /\.(gtl|gbl|gts|gbs|gto|gbo|gm1)$/.test(name))) {
    if (!readFileSync(join(staging, name), 'utf8').includes('M02*')) {
      throw new Error(`Gerber is missing its end marker: ${name}`);
    }
  }
  const edgeGerber = readFileSync(
    join(staging, 'arc58-reversible-Edge_Cuts.gm1'),
    'utf8',
  );
  const profileStrokes = edgeGerber.match(/^X-?\d+Y-?\d+D02\*$/gm) ?? [];
  const expectedStrokes =
    layout.mechanical.boardOutline.length + layout.rgb.ledsPerHalf * 4;
  if (profileStrokes.length !== expectedStrokes) {
    throw new Error(
      `edge profile must contain ${layout.mechanical.boardOutline.length} outer-perimeter ` +
      `strokes plus four sides for each of ${layout.rgb.ledsPerHalf} RGB apertures; ` +
      `expected ${expectedStrokes} strokes, found ${profileStrokes.length}`,
    );
  }
  for (const name of ['arc58-reversible-PTH.drl', 'arc58-reversible-NPTH.drl']) {
    if (!readFileSync(join(staging, name), 'utf8').includes('M30')) {
      throw new Error(`drill file is missing its end marker: ${name}`);
    }
  }

  mkdirSync(dirname(output), { recursive: true });
  rmSync(output, { force: true });
  run('zip', ['-j', output, ...expected.map((name) => join(staging, name))]);
  run('unzip', ['-t', output]);
  console.log(`PASS: wrote ${output}`);
} finally {
  rmSync(tempRoot, { recursive: true, force: true });
}
