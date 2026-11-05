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

const SIZE_KB = 1024;
const SIZE_MB = SIZE_KB * SIZE_KB;
const MEGABYTE_FORMAT = new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

// «812 Б», «44 КБ», «1,2 МБ».
export function formatFileSize(bytes: number): string {
  if (bytes < SIZE_KB) {
    return `${String(bytes)} Б`;
  }
  if (bytes < SIZE_MB) {
    return `${String(Math.round(bytes / SIZE_KB))} КБ`;
  }
  return `${MEGABYTE_FORMAT.format(bytes / SIZE_MB)} МБ`;
}

// The extension after the last dot in capitals, «PDF»; empty when the name has no dot or nothing after it.
export function fileType(name: string): string {
  const dot = name.lastIndexOf('.');
  return dot < 0 ? '' : name.slice(dot + 1).toUpperCase();
}

// «договор.pdf · PDF · 1,2 МБ»; the type or the size is left out when unknown.
export function formatAttachment(attachment: { name: string; size: number | null }): string {
  const type = fileType(attachment.name);
  const parts = [
    attachment.name,
    ...(type === '' ? [] : [type]),
    ...(attachment.size === null ? [] : [formatFileSize(attachment.size)]),
  ];
  return parts.join(' · ');
}
