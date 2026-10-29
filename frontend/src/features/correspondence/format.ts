import type { components } from '../../api/generated/schema';

export type Address = components['schemas']['Address'];

const DATE_FORMAT = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});
const DATE_TIME_FORMAT = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});
const PLURALS = new Intl.PluralRules('ru');

// «29.10.2026» in the user's local time.
export function formatDate(iso: string): string {
  return DATE_FORMAT.format(new Date(iso));
}

// «29.10.2026, 14:05» in the user's local time.
export function formatDateTime(iso: string): string {
  return DATE_TIME_FORMAT.format(new Date(iso));
}

// «1 письмо», «2 письма», «5 писем».
export function emailCountLabel(count: number): string {
  const category = PLURALS.select(count);
  const word = category === 'one' ? 'письмо' : category === 'few' ? 'письма' : 'писем';
  return `${String(count)} ${word}`;
}

// «Имя <адрес>» when the name is known, else the address.
export function formatAddress(address: Address): string {
  const name = address.name ?? '';
  return name === '' ? address.address : `${name} <${address.address}>`;
}

export function formatAddresses(addresses: readonly Address[]): string {
  return addresses.map(formatAddress).join(', ');
}
