import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

// Task 1.2 of 1-8-visual-system: the light and the dark set of color tokens in tokens.css.

const css = readFileSync(resolve(process.cwd(), 'src/styles/tokens.css'), 'utf8');

const DARK_START = /@media\s*\(\s*prefers-color-scheme:\s*dark\s*\)\s*\{/;

// Splits the file into the text outside the dark media block and the text inside it.
function splitSets(source: string): { light: string; dark: string } {
  const match = DARK_START.exec(source);
  if (!match) return { light: source, dark: '' };
  const open = match.index + match[0].length;
  let depth = 1;
  let end = open;
  while (end < source.length && depth > 0) {
    if (source[end] === '{') depth += 1;
    if (source[end] === '}') depth -= 1;
    end += 1;
  }
  return {
    light: source.slice(0, match.index) + source.slice(end),
    dark: source.slice(open, end - 1),
  };
}

function colorTokens(block: string): Map<string, string> {
  const found = new Map<string, string>();
  for (const m of block.matchAll(/(--color-[a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    found.set(m[1] ?? '', (m[2] ?? '').trim());
  }
  return found;
}

const sets = splitSets(css);
const light = colorTokens(sets.light);
const dark = colorTokens(sets.dark);

function channel(hex: string, from: number): number {
  const value = parseInt(hex.slice(from, from + 2), 16) / 255;
  return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  return 0.2126 * channel(hex, 1) + 0.7152 * channel(hex, 3) + 0.0722 * channel(hex, 5);
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return ((hi ?? 0) + 0.05) / ((lo ?? 0) + 0.05);
}

const TEXT_TOKENS = [
  '--color-text',
  '--color-text-muted',
  '--color-link',
  '--color-danger',
  '--color-ok',
];
const GROUNDS = ['--color-background', '--color-surface'];
const OWN_BACKGROUND_PAIRS = [
  'button-primary',
  'button-danger',
  'badge-manual',
  'badge-rule',
  'badge-engine',
].map((kind) => [`--color-${kind}-text`, `--color-${kind}-bg`] as const);

// Every --color-X-text that has a --color-X-bg in either set, plus the five that must exist.
const DERIVED_PAIRS: (readonly [string, string])[] = (() => {
  const names = new Set([...light.keys(), ...dark.keys()]);
  const pairs = new Map<string, readonly [string, string]>();
  for (const [text, background] of OWN_BACKGROUND_PAIRS) pairs.set(text, [text, background]);
  for (const name of names) {
    const background = `${name.slice(0, -'-text'.length)}-bg`;
    if (name.endsWith('-text') && names.has(background)) pairs.set(name, [name, background]);
  }
  return [...pairs.values()];
})();

const SETS = [
  ['light', light],
  ['dark', dark],
] as const;

function expectContrast(set: Map<string, string>, text: string, background: string): void {
  const foreground = set.get(text);
  const ground = set.get(background);
  expect(foreground, text).toMatch(/^#[0-9a-fA-F]{6}$/);
  expect(ground, background).toMatch(/^#[0-9a-fA-F]{6}$/);
  expect(contrast(foreground ?? '#000000', ground ?? '#000000')).toBeGreaterThanOrEqual(4.5);
}

describe('color tokens', () => {
  it('has a dark set in prefers-color-scheme next to the light set', () => {
    expect(DARK_START.test(css)).toBe(true);
    expect(light.size).toBeGreaterThan(0);
    expect(dark.size).toBeGreaterThan(0);
  });

  it('sets color-scheme: light dark on :root', () => {
    expect(sets.light).toMatch(/:root\s*\{[^}]*color-scheme:\s*light\s+dark\s*;/);
  });

  it('declares the dark tokens on :root inside the media block', () => {
    expect(sets.dark).toMatch(/:root\s*\{[^}]*--color-/);
    expect(sets.dark.replace(/:root\s*\{[^}]*\}/, '').trim()).toBe('');
  });

  it('writes every color token of both sets as #rrggbb', () => {
    const malformed = SETS.flatMap(([setName, set]) =>
      [...set]
        .filter(([, value]) => !/^#[0-9a-fA-F]{6}$/.test(value))
        .map(([name, value]) => `${setName} ${name}: ${value}`),
    );

    expect(malformed).toEqual([]);
  });

  it('derives its pairs from the tokens: every -text with a -bg is checked, the named five exist', () => {
    const names = new Set([...light.keys(), ...dark.keys()]);
    for (const [text, background] of OWN_BACKGROUND_PAIRS) {
      expect(names.has(text), text).toBe(true);
      expect(names.has(background), background).toBe(true);
    }
  });

  it('gives every color token a value in the light set and in the dark set', () => {
    const missingInDark = [...light.keys()].filter((name) => !dark.has(name));
    const missingInLight = [...dark.keys()].filter((name) => !light.has(name));

    expect(missingInDark).toEqual([]);
    expect(missingInLight).toEqual([]);
  });

  describe.each(SETS)('contrast in the %s set', (_name, set) => {
    it.each(TEXT_TOKENS.flatMap((text) => GROUNDS.map((ground) => [text, ground] as const)))(
      '%s over %s reaches 4.5:1',
      (text, ground) => {
        expectContrast(set, text, ground);
      },
    );

    it.each(DERIVED_PAIRS)('%s over %s reaches 4.5:1', (text, background) => {
      expectContrast(set, text, background);
    });
  });
});
