// Unit tests of the service table and the local match: the FR-53 and FR-54 scenarios, and the server
// match that picks the «Как исправить» steps (FR-26).
import { describe, expect, it } from 'vitest';

import { MAIL_SERVICES, serviceForAddress, serviceForServer } from './mailServices';

const DOMAINS: readonly (readonly [string, string, string])[] = [
  ['yandex.ru', 'yandex', 'Яндекс Почта'],
  ['ya.ru', 'yandex', 'Яндекс Почта'],
  ['yandex.com', 'yandex', 'Яндекс Почта'],
  ['mail.ru', 'mailru', 'Mail.ru'],
  ['inbox.ru', 'mailru', 'Mail.ru'],
  ['list.ru', 'mailru', 'Mail.ru'],
  ['bk.ru', 'mailru', 'Mail.ru'],
  ['internet.ru', 'mailru', 'Mail.ru'],
  ['gmail.com', 'gmail', 'Gmail'],
  ['googlemail.com', 'gmail', 'Gmail'],
  ['icloud.com', 'icloud', 'iCloud'],
  ['me.com', 'icloud', 'iCloud'],
  ['mac.com', 'icloud', 'iCloud'],
  ['demo.test', 'demo', 'Демо'],
];

describe('serviceForAddress', () => {
  it.each(DOMAINS)('FR-53 «A known domain»: anna@%s is %s', (domain, id, name) => {
    const service = serviceForAddress(`anna@${domain}`);

    expect(service.id).toBe(id);
    expect(service.name).toBe(name);
  });

  it('FR-53 «Case and spaces»: « Anna@Mail.RU » is Mail.ru on imap.mail.ru', () => {
    const service = serviceForAddress(' Anna@Mail.RU ');

    expect(service.id).toBe('mailru');
    expect(service.server).toBe('imap.mail.ru');
  });

  it.each(['anna@outlook.com', 'anna@rambler.ru'])(
    'FR-53 «A service without password sign-in»: %s is «Другой» with an empty server',
    (address) => {
      const service = serviceForAddress(address);

      expect(service.id).toBe('other');
      expect(service.name).toBe('Другой');
      expect(service.server).toBe('');
    },
  );

  it('FR-53 «An unknown domain»: anna@studio-anna.ru is «Другой» with the port 993 and no steps', () => {
    const service = serviceForAddress('anna@studio-anna.ru');

    expect(service.id).toBe('other');
    expect(service.server).toBe('');
    expect(service.port).toBe(993);
    expect(service.steps).toEqual([]);
    expect(service.help).toBeNull();
    expect(service.howToTitle).toBeNull();
  });

  it.each(['anna', 'anna.yandex.ru', ''])(
    'FR-53: «%s» (no «@» or empty) is «Другой»',
    (address) => {
      expect(serviceForAddress(address).id).toBe('other');
    },
  );

  it('FR-53 «The demo mailbox»: demo.test is «Демо» on greenmail:3143 without steps', () => {
    const service = serviceForAddress('anna@demo.test');

    expect(service.server).toBe('greenmail');
    expect(service.port).toBe(3143);
    expect(service.steps).toEqual([]);
    expect(service.help).toBeNull();
    expect(service.howToTitle).toBeNull();
  });

  it('FR-53 «A known domain»: Яндекс Почта is imap.yandex.ru on 993', () => {
    const service = serviceForAddress('anna@yandex.ru');

    expect(service.server).toBe('imap.yandex.ru');
    expect(service.port).toBe(993);
  });
});

describe('serviceForServer', () => {
  it.each([
    ['imap.yandex.ru', 'yandex'],
    ['imap.mail.ru', 'mailru'],
    ['imap.gmail.com', 'gmail'],
    ['imap.mail.me.com', 'icloud'],
    ['greenmail', 'demo'],
  ])('FR-26 «The steps for a refused sign-in»: %s is the service %s', (server, id) => {
    expect(serviceForServer(server)?.id).toBe(id);
  });

  it('FR-26 «No steps for an unknown server»: imap.studio-anna.ru has no service', () => {
    expect(serviceForServer('imap.studio-anna.ru')).toBeNull();
  });

  it('FR-26: an empty server has no service', () => {
    expect(serviceForServer('')).toBeNull();
  });
});

describe('MAIL_SERVICES', () => {
  it.each(['yandex', 'mailru', 'gmail', 'icloud'])(
    'FR-54 «Every real service has steps and a link»: %s has a title, a step and an https link',
    (id) => {
      const service = MAIL_SERVICES.find((candidate) => candidate.id === id);

      expect(service).toBeDefined();
      expect(service?.howToTitle).toMatch(/^Как подключить /);
      expect(service?.steps.length).toBeGreaterThanOrEqual(1);
      expect(service?.help?.url.startsWith('https://')).toBe(true);
    },
  );

  it('FR-54 «Steps of Яндекс Почта»: the title, the steps and the link label are exact', () => {
    const yandex = MAIL_SERVICES.find((service) => service.id === 'yandex');

    expect(yandex?.howToTitle).toBe('Как подключить Яндекс Почту');
    expect(yandex?.steps).toEqual([
      'Включите доступ по IMAP: Настройки → Почтовые программы → «С сервера imap.yandex.ru по протоколу IMAP» и «Пароли приложений и OAuth-токены».',
      'Создайте пароль приложения для почты: Яндекс ID → Безопасность → Пароли приложений. Он начнёт действовать через 2–3 часа.',
    ]);
    expect(yandex?.help?.label).toBe('Справка Яндекс Почты');
  });
});
