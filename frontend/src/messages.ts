// Russian UI texts that the server does not send: the rest comes from the API's error messages.
export const SERVER_UNAVAILABLE_MESSAGE = 'Сервер не отвечает';
export const LOADING_MESSAGE = 'Загрузка…';
export const INVALID_LINK_MESSAGE = 'Ссылка недействительна или устарела';
export const REGISTRATION_MAIL_FAILED_MESSAGE =
  'Не удалось отправить письмо. Попробуйте зарегистрироваться ещё раз позже';
export const PASSWORD_RESET_REQUESTED_MESSAGE =
  'Если такой email зарегистрирован, мы отправили на него ссылку для сброса пароля';
export const PASSWORD_CHANGED_MESSAGE = 'Пароль изменён. Теперь можно войти';
export const NOT_FOUND_TITLE = 'Страница не найдена';

export function confirmationSentMessage(email: string): string {
  return `Мы отправили письмо со ссылкой для подтверждения на ${email}`;
}
