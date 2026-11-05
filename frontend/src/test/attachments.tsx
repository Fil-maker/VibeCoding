import { vi } from 'vitest';

import { ANNA, json, renderApp, type Handler, type Rendered } from './appHarness';

// Harness of the attachment tests: a chain page with one email, the download answers of the server and
// the way the browser saves a file (an object URL on a link with the `download` attribute).

export const CHAIN_ID = 'bbbbbbbb-0000-4000-8000-000000000001';
export const EMAIL_ID = 'cccccccc-0000-4000-8000-000000000001';

export interface AttachmentJson {
  index: number;
  name: string;
  size: number | null;
}

export function attachmentPath(index: number): string {
  return `/emails/${EMAIL_ID}/attachments/${String(index)}`;
}

// What the server answers to a successful download: the bytes, always for saving.
export function fileAnswer(content: string, name: string): Handler {
  return () =>
    new Response(content, {
      status: 200,
      headers: {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(name)}`,
        'X-Content-Type-Options': 'nosniff',
      },
    });
}

// A refused download: the error envelope of the API.
export function downloadError(status: number, code: string, message: string): Handler {
  return () => json(status, { error: { code, message } });
}

// The chain page of CHAIN_ID with one email that carries `attachments`; `downloads` answers by index.
export function openChainWith(
  attachments: AttachmentJson[],
  downloads: Record<number, Handler> = {},
): Rendered {
  const routes: Record<string, Handler> = {
    [`GET /reply-chains/${CHAIN_ID}`]: () =>
      json(200, {
        id: CHAIN_ID,
        subject: 'Договор поставки',
        participants: [{ address: 'oleg@stroy.test', name: null }],
        emails: [
          {
            id: EMAIL_ID,
            sender: { address: 'oleg@stroy.test', name: null },
            to: [{ address: 'anna@yandex.ru', name: null }],
            cc: [],
            sent_at: '2026-10-20T09:00:00Z',
            subject: 'Договор поставки',
            text: 'Текст письма',
            attachments,
          },
        ],
      }),
  };
  for (const [index, handler] of Object.entries(downloads)) {
    routes[`GET ${attachmentPath(Number(index))}`] = handler;
  }
  return renderApp({ path: `/chains/${CHAIN_ID}`, me: ANNA, routes });
}

export interface SavedFile {
  name: string;
  url: string;
  blob: Blob;
}

// Replaces the browser's saving: object URLs are fake, and a click on a link with `download` is recorded
// instead of navigating. Returns the files saved so far.
export function captureSavedFiles(): SavedFile[] {
  const saved: SavedFile[] = [];
  const blobs = new Map<string, Blob>();
  let counter = 0;
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: (blob: Blob): string => {
      counter += 1;
      const url = `blob:saved-${String(counter)}`;
      blobs.set(url, blob);
      return url;
    },
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: (): void => undefined,
  });
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    const blob = blobs.get(this.href);
    if (this.hasAttribute('download') && blob) {
      saved.push({ name: this.download, url: this.href, blob });
    }
  });
  return saved;
}
