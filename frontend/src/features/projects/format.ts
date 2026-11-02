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

// «Движок text-1 · сходство 43%»: the similarity (0–1) in whole percent.
export function placementLabel(engineVersion: string, similarity: number): string {
  return `Движок ${engineVersion} · сходство ${String(Math.round(similarity * 100))}%`;
}
