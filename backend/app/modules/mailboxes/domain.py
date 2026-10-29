"""Pure rules of mailboxes: the Russian reason of a failed read."""

from app.modules.mailboxes.models import MailboxErrorCode, MailboxStatus

STATUS_ERROR_MESSAGES: dict[MailboxErrorCode, str] = {
    MailboxErrorCode.SIGN_IN_FAILED: (
        "не удалось войти в ящик, подключите его заново с новым паролем приложения"
    ),
    MailboxErrorCode.UNREACHABLE: "сервер не отвечает",
    MailboxErrorCode.READ_FAILED: "не удалось прочитать письма",
}


def describe_status_error(status: str, error_code: str | None) -> str | None:
    """The reason to show next to the status `failed`; nothing for any other status."""
    if status != MailboxStatus.FAILED or error_code is None:
        return None
    try:
        return STATUS_ERROR_MESSAGES[MailboxErrorCode(error_code)]
    except (ValueError, KeyError):
        return STATUS_ERROR_MESSAGES[MailboxErrorCode.READ_FAILED]
