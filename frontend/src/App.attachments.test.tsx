import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  attachmentPath,
  captureSavedFiles,
  downloadError,
  fileAnswer,
  openChainWith,
  type AttachmentJson,
} from './test/attachments';
import { callsTo, json, type Handler } from './test/appHarness';

afterEach(() => {
  vi.restoreAllMocks();
});

async function attachmentButton(name: string): Promise<HTMLElement> {
  return screen.findByRole('button', { name });
}

// The widest ancestor of the button that holds no other attachment button: the attachment's own block.
function blockOf(button: HTMLElement, all: HTMLElement[]): HTMLElement {
  let block = button;
  for (;;) {
    const parent = block.parentElement;
    if (!parent || all.filter((other) => parent.contains(other)).length > 1) return block;
    block = parent;
  }
}

describe('attachments on the chain page', () => {
  it('FR-31 «Reading a chain»: an attachment reads «договор.pdf · PDF · 1,2 МБ»', async () => {
    openChainWith([{ index: 0, name: 'договор.pdf', size: 1258291 }]);

    expect(await attachmentButton('договор.pdf · PDF · 1,2 МБ')).toBeInTheDocument();
  });

  it('FR-31 «Small and nameless types»: «смета.xlsx · XLSX · 812 Б» and «README · 44 КБ»', async () => {
    openChainWith([
      { index: 0, name: 'смета.xlsx', size: 812 },
      { index: 1, name: 'README', size: 45000 },
    ]);

    expect(await attachmentButton('смета.xlsx · XLSX · 812 Б')).toBeInTheDocument();
    expect(await attachmentButton('README · 44 КБ')).toBeInTheDocument();
  });

  it('FR-31 «An attachment read before sizes were kept»: «акт.pdf · PDF» without a size', async () => {
    openChainWith([{ index: 0, name: 'акт.pdf', size: null }]);

    const button = await attachmentButton('акт.pdf · PDF');
    expect(button).toHaveTextContent(/^акт\.pdf · PDF$/);
  });

  it('FR-31 «An attachment read before sizes were kept»: «акт.pdf · PDF» can be downloaded', async () => {
    const saved = captureSavedFiles();
    const rendered = openChainWith([{ index: 0, name: 'акт.pdf', size: null }], {
      0: fileAnswer('содержимое акта', 'акт.pdf'),
    });

    fireEvent.click(await attachmentButton('акт.pdf · PDF'));

    await waitFor(() => {
      expect(saved).toHaveLength(1);
    });
    expect(callsTo(rendered, 'GET', attachmentPath(0))).toHaveLength(1);
    expect(saved[0]?.name).toBe('акт.pdf');
    expect(await saved[0]?.blob.text()).toBe('содержимое акта');
  });

  it('FR-57 «Downloading a contract»: a click asks for the attachment and saves «договор.pdf» with its bytes', async () => {
    const saved = captureSavedFiles();
    const rendered = openChainWith([{ index: 0, name: 'договор.pdf', size: 12 }], {
      0: fileAnswer('%PDF-содержимое', 'договор.pdf'),
    });

    fireEvent.click(await attachmentButton('договор.pdf · PDF · 12 Б'));

    await waitFor(() => {
      expect(saved).toHaveLength(1);
    });
    expect(callsTo(rendered, 'GET', attachmentPath(0))).toHaveLength(1);
    expect(saved[0]?.name).toBe('договор.pdf');
    expect(await saved[0]?.blob.text()).toBe('%PDF-содержимое');
  });

  it('FR-57 «Two attachments with one name»: a click on the second asks for and saves the second', async () => {
    const saved = captureSavedFiles();
    const rendered = openChainWith(
      [
        { index: 0, name: 'скан.jpg', size: 100 },
        { index: 1, name: 'скан.jpg', size: 250 },
      ],
      { 0: fileAnswer('первый', 'скан.jpg'), 1: fileAnswer('второй', 'скан.jpg') },
    );

    await screen.findAllByRole('button', { name: /^скан\.jpg/ });
    const second = screen.getByRole('button', { name: 'скан.jpg · JPG · 250 Б' });
    fireEvent.click(second);

    await waitFor(() => {
      expect(saved).toHaveLength(1);
    });
    expect(callsTo(rendered, 'GET', attachmentPath(1))).toHaveLength(1);
    expect(callsTo(rendered, 'GET', attachmentPath(0))).toHaveLength(0);
    expect(saved[0]?.name).toBe('скан.jpg');
    expect(await saved[0]?.blob.text()).toBe('второй');
  });

  it('FR-57 «An HTML attachment»: «счёт.html» is saved, not opened, and no script runs', async () => {
    const saved = captureSavedFiles();
    openChainWith([{ index: 0, name: 'счёт.html', size: 25 }], {
      0: fileAnswer('<script>alert(1)</script>', 'счёт.html'),
    });

    fireEvent.click(await attachmentButton('счёт.html · HTML · 25 Б'));

    await waitFor(() => {
      expect(saved).toHaveLength(1);
    });
    expect(saved[0]?.name).toBe('счёт.html');
    expect(document.body.querySelector('script')).toBeNull();
  });
});

describe('attachments that cannot be fetched', () => {
  const TWO: AttachmentJson[] = [
    { index: 0, name: 'договор.pdf', size: 1000 },
    { index: 1, name: 'смета.xlsx', size: 812 },
  ];

  async function bothButtons(): Promise<[HTMLElement, HTMLElement]> {
    return [
      await attachmentButton('договор.pdf · PDF · 1000 Б'),
      await attachmentButton('смета.xlsx · XLSX · 812 Б'),
    ];
  }

  it.each([
    [
      'FR-58 «No connected mailbox holds the email»',
      409,
      'mailbox_disconnected',
      'Файл недоступен: ящик отключён',
    ],
    [
      'FR-58 «The email is gone from the mailbox»',
      410,
      'email_gone',
      'Письмо больше не найдено в ящике',
    ],
    [
      'FR-58 «The server refuses the sign-in»',
      502,
      'mailbox_sign_in_failed',
      'Не удалось получить файл: не удалось войти в ящик',
    ],
    [
      'FR-58 «The server does not answer»',
      504,
      'mailbox_unreachable',
      'Не удалось получить файл: сервер не отвечает',
    ],
  ])(
    '%s: the message is shown under that attachment only and nothing is saved',
    async (_name, status, code, message) => {
      const saved = captureSavedFiles();
      const rendered = openChainWith(TWO, { 0: downloadError(status, code, message) });
      const [first, second] = await bothButtons();

      fireEvent.click(first);

      const text = await screen.findByText(message);
      const all = [first, second];
      expect(blockOf(first, all)).toContainElement(text);
      expect(blockOf(second, all)).not.toContainElement(text);
      expect(screen.getAllByText(message)).toHaveLength(1);
      expect(callsTo(rendered, 'GET', attachmentPath(0))).toHaveLength(1);
      expect(callsTo(rendered, 'GET', attachmentPath(1))).toHaveLength(0);
      expect(saved).toHaveLength(0);
    },
  );

  it('FR-58 «The server does not answer»: a later click downloads the file once the server answers', async () => {
    const saved = captureSavedFiles();
    let answering = false;
    const flaky: Handler = (body, session) =>
      answering
        ? fileAnswer('содержимое', 'договор.pdf')(body, session)
        : json(504, {
            error: {
              code: 'mailbox_unreachable',
              message: 'Не удалось получить файл: сервер не отвечает',
            },
          });
    openChainWith(TWO, { 0: flaky });
    const [first] = await bothButtons();

    fireEvent.click(first);
    await screen.findByText('Не удалось получить файл: сервер не отвечает');
    expect(saved).toHaveLength(0);
    answering = true;
    fireEvent.click(first);

    await waitFor(() => {
      expect(saved).toHaveLength(1);
    });
    expect(saved[0]?.name).toBe('договор.pdf');
    expect(await saved[0]?.blob.text()).toBe('содержимое');
  });
});
