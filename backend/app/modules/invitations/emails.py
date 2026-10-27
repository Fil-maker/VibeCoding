"""The invitation email."""

from app.platform.mail import OutgoingEmail, build_link


def invitation_email(
    *, to: str, organization_name: str, app_base_url: str, token: str, days: int
) -> OutgoingEmail:
    """The email with the invitation link and its lifetime."""
    link = build_link(app_base_url, "invitation", token)
    text = (
        f"Вас приглашают в организацию «{organization_name}» в VibeCoding.\n\n"
        "Чтобы принять приглашение, перейдите по ссылке:\n"
        f"{link}\n\n"
        f"Ссылка действительна {days} дн. и работает один раз.\n"
    )
    return OutgoingEmail(
        to=to, subject=f"Приглашение в {organization_name} — VibeCoding", text=text
    )
