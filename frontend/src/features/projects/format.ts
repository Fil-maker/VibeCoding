const PLURALS = new Intl.PluralRules('ru');

function pluralWord(count: number, one: string, few: string, many: string): string {
  const category = PLURALS.select(count);
  const word = category === 'one' ? one : category === 'few' ? few : many;
  return `${String(count)} ${word}`;
}

// «1 цепочка», «2 цепочки», «5 цепочек».
export function chainCountLabel(count: number): string {
  return pluralWord(count, 'цепочка', 'цепочки', 'цепочек');
}

// «1 неразобранная», «2 неразобранные», «5 неразобранных».
export function unassignedCountLabel(count: number): string {
  return pluralWord(count, 'неразобранная', 'неразобранные', 'неразобранных');
}

const RULE_CONDITION_TEXT = { address: 'адрес', domain: 'домен', subject: 'слова темы' } as const;

// «Вручную» for a placement by hand, «Правило · адрес x» for a rule (subject words in «»), else
// «Движок text-1 · сходство 43%»: the similarity (0–1) in whole percent.
export function placementLabel(placement: {
  kind: 'engine' | 'manual' | 'rule';
  engine_version?: string | null;
  similarity?: number | null;
  rule?: { condition: 'address' | 'domain' | 'subject'; value: string } | null;
}): string {
  if (placement.kind === 'manual') {
    return 'Вручную';
  }
  if (placement.kind === 'rule' && placement.rule !== undefined && placement.rule !== null) {
    const { condition, value } = placement.rule;
    const shown = condition === 'subject' ? `«${value}»` : value;
    return `Правило · ${RULE_CONDITION_TEXT[condition]} ${shown}`;
  }
  const percent = Math.round((placement.similarity ?? 0) * 100);
  return `Движок ${placement.engine_version ?? ''} · сходство ${String(percent)}%`;
}
