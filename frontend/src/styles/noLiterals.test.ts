import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

// Task 1.2 of 1-8-visual-system: no color or pixel size is written outside tokens.css.

const SRC = `${resolve(process.cwd(), 'src').replaceAll('\\', '/')}/`;

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = `${dir}${entry.name}`;
    if (entry.isDirectory()) return entry.name === 'generated' ? [] : walk(`${path}/`);
    return [path];
  });
}

const files = walk(SRC).map((path) => path.slice(SRC.length));

// Component sources: the .tsx files that are not tests or test helpers.
const components = files.filter(
  (file) => file.endsWith('.tsx') && !file.endsWith('.test.tsx') && !file.startsWith('test/'),
);

const NAMED = [
  'red',
  'green',
  'blue',
  'white',
  'black',
  'gray',
  'grey',
  'orange',
  'yellow',
  'purple',
  'pink',
  'brown',
  'teal',
  'navy',
  'maroon',
  'silver',
  'gold',
  'crimson',
  'tomato',
].join('|');

const read = (file: string): string => readFileSync(`${SRC}${file}`, 'utf8');

// Stylesheets other than the token file: CSS modules keep no raw color or size.
const stylesheets = files.filter((file) => file.endsWith('.css') && file !== 'styles/tokens.css');

const COLOR_PROPERTY = String.raw`(?:color|background(?:-color)?|border[\w-]*|outline[\w-]*|fill|stroke)`;
const NAMED_IN_CSS = new RegExp(
  String.raw`(?:^|[;{\s])${COLOR_PROPERTY}\s*:[^;}]*(?<![-\w])(?:${NAMED})(?![-\w])`,
  'im',
);
const NAMED_IN_TSX = new RegExp(String.raw`(["'\x60])(?:${NAMED})\1|color:\s*(?:${NAMED})\b`, 'i');

const withoutComments = (text: string): string => text.replace(/\/\*[\s\S]*?\*\//g, '');

const CHECKS = [
  ['a hex color', /#[0-9a-fA-F]{3,8}\b/, /#[0-9a-fA-F]{3,8}\b/],
  ['rgb(', /\brgba?\(/i, /\brgba?\(/i],
  ['hsl(', /\bhsla?\(/i, /\bhsla?\(/i],
  ['a named color', NAMED_IN_TSX, NAMED_IN_CSS],
  ['a px value', /\b\d+(\.\d+)?px\b/, /\b\d+(\.\d+)?px\b/],
] as const;

describe('literals outside tokens.css', () => {
  it('scans the component sources and the CSS modules', () => {
    expect(components).toContain('App.tsx');
    expect(stylesheets).toContain('components/ui.module.css');
  });

  it.each(CHECKS)('has no .tsx with %s', (_what, pattern) => {
    const offenders = components.filter((file) => pattern.test(read(file)));

    expect(offenders).toEqual([]);
  });

  it.each(CHECKS)('has no .css but tokens.css with %s', (_what, _tsx, pattern) => {
    const offenders = stylesheets.filter((file) => pattern.test(withoutComments(read(file))));

    expect(offenders).toEqual([]);
  });

  it('has no <button outside components/Button.tsx', () => {
    const offenders = components.filter(
      (file) => file !== 'components/Button.tsx' && /<button\b/.test(read(file)),
    );

    expect(offenders).toEqual([]);
  });

  it('has no .tsx with style={{', () => {
    const offenders = components.filter((file) => read(file).includes('style={{'));

    expect(offenders).toEqual([]);
  });
});
