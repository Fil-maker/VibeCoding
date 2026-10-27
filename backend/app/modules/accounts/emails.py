"""The confirmation email."""

from app.platform.mail import OutgoingEmail, build_link


def confirmation_email(
    *, to: str, name: str, app_base_url: str, token: str, hours: int
) -> OutgoingEmail:
    """The email with the confirmation link and its lifetime."""
    link = build_link(app_base_url, "confirm-email", token)
    text = (
        f"Здравствуйте, {name}!\n\n"
        "Чтобы подтвердить регистрацию в VibeCoding, перейдите по ссылке:\n"
        f"{link}\n\n"
        f"Ссылка действительна {hours} ч и работает один раз.\n"
    )
    return OutgoingEmail(to=to, subject="Подтвердите регистрацию в VibeCoding", text=text)
