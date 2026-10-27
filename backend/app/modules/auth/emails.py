"""The password reset email."""

from app.platform.mail import OutgoingEmail, build_link


def password_reset_email(
    *, to: str, name: str, app_base_url: str, token: str, minutes: int
) -> OutgoingEmail:
    """The email with the reset link and its lifetime."""
    link = build_link(app_base_url, "reset-password", token)
    text = (
        f"Здравствуйте, {name}!\n\n"
        "Чтобы задать новый пароль в VibeCoding, перейдите по ссылке:\n"
        f"{link}\n\n"
        f"Ссылка действительна {minutes} мин и работает один раз. "
        "Если вы не запрашивали сброс, просто проигнорируйте это письмо.\n"
    )
    return OutgoingEmail(to=to, subject="Сброс пароля в VibeCoding", text=text)
