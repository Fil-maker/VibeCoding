// The built-in table of mail services and the local match of an address or a server to one of them.
// Nothing here makes a request, so a typed address never leaves the browser through this module.

export type MailServiceId = 'yandex' | 'mailru' | 'gmail' | 'icloud' | 'demo' | 'other';

export interface MailService {
  id: MailServiceId;
  name: string;
  howToTitle: string | null;
  server: string;
  port: number;
  steps: readonly string[];
  help: { label: string; url: string } | null;
}

const IMAP_PORT = 993;
const DEMO_PORT = 3143;

const OTHER_SERVICE: MailService = {
  id: 'other',
  name: 'Другой',
  howToTitle: null,
  server: '',
  port: IMAP_PORT,
  steps: [],
  help: null,
};

// The app's own list of mail services; static data, so no request carries a typed address.
export const MAIL_SERVICES: readonly MailService[] = [
  {
    id: 'yandex',
    name: 'Яндекс Почта',
    howToTitle: 'Как подключить Яндекс Почту',
    server: 'imap.yandex.ru',
    port: IMAP_PORT,
    steps: [
      'Включите доступ по IMAP: Настройки → Почтовые программы → «С сервера imap.yandex.ru по протоколу IMAP» и «Пароли приложений и OAuth-токены».',
      'Создайте пароль приложения для почты: Яндекс ID → Безопасность → Пароли приложений. Он начнёт действовать через 2–3 часа.',
    ],
    help: {
      label: 'Справка Яндекс Почты',
      url: 'https://yandex.ru/support/yandex-360/customers/mail/ru/mail-clients/others',
    },
  },
  {
    id: 'mailru',
    name: 'Mail.ru',
    howToTitle: 'Как подключить Mail.ru',
    server: 'imap.mail.ru',
    port: IMAP_PORT,
    steps: [
      'Привяжите к ящику номер телефона: без него пароль для внешних приложений не создать.',
      'Создайте пароль для внешнего приложения: Настройки → Все настройки → Безопасность → Пароли для внешних приложений.',
    ],
    help: { label: 'Справка Mail.ru', url: 'https://help.mail.ru/mail/login/mailer/' },
  },
  {
    id: 'gmail',
    name: 'Gmail',
    howToTitle: 'Как подключить Gmail',
    server: 'imap.gmail.com',
    port: IMAP_PORT,
    steps: [
      'Доступ по IMAP в Gmail включён всегда, включать его не нужно.',
      'Включите двухэтапную аутентификацию в аккаунте Google: без неё пароль приложения не создать.',
      'Создайте пароль приложения на странице myaccount.google.com/apppasswords.',
    ],
    help: {
      label: 'Справка Google',
      url: 'https://support.google.com/accounts/answer/185833?hl=ru',
    },
  },
  {
    id: 'icloud',
    name: 'iCloud',
    howToTitle: 'Как подключить iCloud',
    server: 'imap.mail.me.com',
    port: IMAP_PORT,
    steps: [
      'Включите двухфакторную аутентификацию для Apple ID: без неё пароль приложения не создать.',
      'Создайте пароль для приложения: account.apple.com → Вход и безопасность → Пароли приложений.',
    ],
    help: { label: 'Справка Apple', url: 'https://support.apple.com/ru-ru/102654' },
  },
  {
    id: 'demo',
    name: 'Демо',
    howToTitle: null,
    server: 'greenmail',
    port: DEMO_PORT,
    steps: [],
    help: null,
  },
  OTHER_SERVICE,
];

const DOMAINS: Readonly<Record<string, MailServiceId>> = {
  'yandex.ru': 'yandex',
  'ya.ru': 'yandex',
  'yandex.com': 'yandex',
  'mail.ru': 'mailru',
  'inbox.ru': 'mailru',
  'list.ru': 'mailru',
  'bk.ru': 'mailru',
  'internet.ru': 'mailru',
  'gmail.com': 'gmail',
  'googlemail.com': 'gmail',
  'icloud.com': 'icloud',
  'me.com': 'icloud',
  'mac.com': 'icloud',
  'demo.test': 'demo',
};

export function serviceById(id: MailServiceId): MailService {
  return MAIL_SERVICES.find((service) => service.id === id) ?? OTHER_SERVICE;
}

// The part of an address after «@», trimmed and lowercased; '' when there is none.
export function domainOfAddress(address: string): string {
  const at = address.lastIndexOf('@');
  return at < 0
    ? ''
    : address
        .slice(at + 1)
        .trim()
        .toLowerCase();
}

export function serviceForAddress(address: string): MailService {
  return serviceById(DOMAINS[domainOfAddress(address)] ?? 'other');
}

export function serviceForServer(server: string): MailService | null {
  const wanted = server.trim().toLowerCase();
  if (wanted === '') {
    return null;
  }
  return MAIL_SERVICES.find((service) => service.server === wanted) ?? null;
}
