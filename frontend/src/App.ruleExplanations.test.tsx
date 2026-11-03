import { describe, expect, it } from 'vitest';

import {
  ESTIMATE_THREAD,
  OFFICE,
  locationAround,
  openChain,
  placed,
  type PlacementJson,
} from './test/chainPlacement';
import { chain, chainRow, openProject, treeOf, type RuleRefJson } from './test/projectTrees';

// Dates are shown in the machine's time zone; the tests pin it to UTC so the day never shifts.
process.env.TZ = 'UTC';

const CASES: [string, string, RuleRefJson][] = [
  [
    'by address',
    'Правило · адрес s.petrov@stroymaster.example',
    { condition: 'address', value: 's.petrov@stroymaster.example' },
  ],
  [
    'by domain',
    'Правило · домен techsnab.example',
    { condition: 'domain', value: 'techsnab.example' },
  ],
  [
    'by subject words',
    'Правило · слова темы «акт работ»',
    { condition: 'subject', value: 'акт работ' },
  ],
];

function byRule(rule: RuleRefJson): PlacementJson {
  return { kind: 'rule', engine_version: null, similarity: null, rule };
}

describe('placement explained: a rule', () => {
  it.each(CASES)(
    'FR-37 «A chain placed by a rule»: in the project tree a chain placed %s shows «%s» and no similarity',
    async (_kind, text, rule) => {
      openProject({
        tree: treeOf(chain(4, { subject: 'Акт скрытых работ', placement: byRule(rule) })),
      });

      const row = await chainRow('Акт скрытых работ');
      expect(row).toHaveTextContent(text);
      expect(row).not.toHaveTextContent('Движок');
      expect(row).not.toHaveTextContent('сходство');
      expect(row).not.toHaveTextContent('Вручную');
    },
  );

  it('FR-37 «A chain placed by a rule»: a chain of «Неразобранное» shows the rule too', async () => {
    openProject({
      tree: {
        ...treeOf(chain(4)),
        counterparties: [],
        unassigned: [
          chain(5, {
            subject: 'Отпуск в июле',
            placement: byRule({ condition: 'subject', value: 'отпуск' }),
          }),
        ],
      },
    });

    const row = await chainRow('Отпуск в июле');
    expect(row).toHaveTextContent('Правило · слова темы «отпуск»');
    expect(row).not.toHaveTextContent('Движок');
    expect(row).not.toHaveTextContent('сходство');
  });

  it.each(CASES)(
    'FR-37 «A chain placed by a rule»: on the chain page a chain placed %s shows «<project> → <thread> · %s» and no similarity',
    async (_kind, text, rule) => {
      openChain({
        subject: 'Акт скрытых работ',
        location: placed(OFFICE, ESTIMATE_THREAD, byRule(rule)),
      });

      const block = await locationAround('Ремонт офиса');
      expect(block).toHaveTextContent(`Ремонт офиса → Смета на ремонт офиса · ${text}`);
      expect(block).not.toHaveTextContent('Движок');
      expect(block).not.toHaveTextContent('сходство');
    },
  );

  it('FR-37 «A chain placed by a rule»: on the chain page a rule chain in «Неразобранное» shows «Ремонт офиса → Неразобранное · Правило · домен techsnab.example»', async () => {
    openChain({
      subject: 'Заказ мониторов',
      location: placed(OFFICE, null, byRule({ condition: 'domain', value: 'techsnab.example' })),
    });

    const block = await locationAround('Ремонт офиса');
    expect(block).toHaveTextContent(
      'Ремонт офиса → Неразобранное · Правило · домен techsnab.example',
    );
    expect(block).not.toHaveTextContent('Движок');
    expect(block).not.toHaveTextContent('сходство');
  });
});
