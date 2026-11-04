import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { type } from './test/appHarness';
import {
  EXPLANATION,
  openForm,
  field,
  pickService,
  howToBlock,
  stepsOf,
  helpHref,
  expectNoHowTo,
  formOf,
} from './test/mailboxForm';

process.env.TZ = 'UTC';

describe('connect form: how to connect (FR-54)', () => {
  it('FR-54 «The explanation»: the text stands above the form', async () => {
    await openForm();

    const text = screen.getByText(EXPLANATION);

    expect(formOf().compareDocumentPosition(text) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy();
  });

  it('FR-54 «Steps of Яндекс Почта»: the region holds both steps as a list and the link «Справка Яндекс Почты»', async () => {
    await openForm();

    type('Адрес почты', 'anna@yandex.ru');

    const block = await howToBlock('Как подключить Яндекс Почту');
    expect(stepsOf(block)).toEqual([
      'Включите доступ по IMAP: Настройки → Почтовые программы → «С сервера imap.yandex.ru по протоколу IMAP» и «Пароли приложений и OAuth-токены».',
      'Создайте пароль приложения для почты: Яндекс ID → Безопасность → Пароли приложений. Он начнёт действовать через 2–3 часа.',
    ]);
    const url = new URL(
      within(block).getByRole('link', { name: 'Справка Яндекс Почты' }).getAttribute('href') ?? '',
    );
    expect(url.protocol).toBe('https:');
    expect(url.hostname).toMatch(/(^|\.)yandex\.ru$/);
  });

  it('FR-54 «Gmail needs no IMAP switch»: one step says IMAP is always on, others ask for 2-step verification and an app password', async () => {
    await openForm();

    type('Адрес почты', 'anna@gmail.com');

    const block = await howToBlock('Как подключить Gmail');
    const steps = stepsOf(block);
    expect(
      steps.some(
        (step) => step.includes('IMAP') && /(всегда\s+включ[её]н|включ[её]н\s+всегда)/i.test(step),
      ),
    ).toBe(true);
    expect(steps.some((step) => /двухэтапн/i.test(step))).toBe(true);
    expect(steps.some((step) => /пароль приложения/i.test(step))).toBe(true);
    expect(helpHref(block).protocol).toBe('https:');
    expect(helpHref(block).hostname).toBe('support.google.com');
  });

  it.each([
    ['anna@mail.ru', 'Как подключить Mail.ru', /(^|\.)mail\.ru$/],
    ['anna@gmail.com', 'Как подключить Gmail', /^support\.google\.com$/],
    ['anna@icloud.com', 'Как подключить iCloud', /(^|\.)(apple|icloud)\.com$/],
  ])(
    'FR-54 «Every real service has steps and a link»: %s shows «%s» with steps, one about the password, and an https link',
    async (address, title, host) => {
      await openForm();

      type('Адрес почты', address);

      const block = await howToBlock(title);
      const steps = stepsOf(block);
      expect(steps.length).toBeGreaterThanOrEqual(1);
      expect(steps.some((step) => /парол/i.test(step))).toBe(true);
      expect(helpHref(block).protocol).toBe('https:');
      expect(helpHref(block).hostname).toMatch(host);
    },
  );

  it.each(['anna@demo.test', 'anna@studio-anna.ru'])(
    'FR-54 «No steps for the demo and an unknown service»: %s shows no «Как подключить» region and no help link on the page',
    async (address) => {
      await openForm();

      type('Адрес почты', address);

      expectNoHowTo();
    },
  );

  it('FR-54 «For a picked service»: Gmail picked by hand over a studio address shows «Как подключить Gmail»', async () => {
    await openForm();
    type('Адрес почты', 'anna@studio-anna.ru');

    pickService('Gmail');

    const block = await howToBlock('Как подключить Gmail');
    expect(stepsOf(block).length).toBeGreaterThanOrEqual(1);
    expect(within(block).getByRole('link')).toBeInTheDocument();
  });

  it('FR-54 «For a picked service»: «Другой» picked by hand over a Яндекс address hides the block and the link', async () => {
    await openForm();
    type('Адрес почты', 'anna@yandex.ru');
    await howToBlock('Как подключить Яндекс Почту');

    pickService('Другой');

    expect(field('Почтовый сервис')).toHaveDisplayValue('Другой');
    expectNoHowTo();
  });

  it('FR-54 «The link carries no address»: new tab, noopener, no part of the address in the URL', async () => {
    await openForm();
    type('Адрес почты', 'anna@yandex.ru');

    const link = await screen.findByRole('link', { name: 'Справка Яндекс Почты' });

    expect(link).toHaveAttribute('target', '_blank');
    expect(link.getAttribute('rel')).toContain('noopener');
    const href = link.getAttribute('href') ?? '';
    expect(href.startsWith('https://')).toBe(true);
    expect(href).not.toContain('anna');
    expect(href).not.toContain('@');
  });
});
