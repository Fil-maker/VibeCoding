"""HTTP entry of sign-in, sessions, email confirmation and password reset."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response

from app.modules.auth.dependencies import SESSION_COOKIE, current_user, set_session_cookie
from app.modules.auth.errors import (
    AccountDisabled,
    EmailNotConfirmed,
    InvalidCredentials,
    InvalidLink,
    NotSignedIn,
    SignInLocked,
)
from app.modules.auth.schemas import (
    EmailConfirmationRequest,
    Me,
    PasswordResetCompletion,
    PasswordResetRequest,
    SignInRequest,
)
from app.modules.auth.service import AuthService, get_auth_service
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock, get_clock
from app.platform.errors import HttpError, error_responses
from app.platform.mail import MailSender, get_mail_sender
from app.platform.settings import Settings, get_settings

# How each domain error of the module is answered over HTTP.
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    InvalidLink: HttpError(400, "invalid_link", "Ссылка недействительна или устарела"),
    InvalidCredentials: HttpError(401, "invalid_credentials", "Неверный email или пароль"),
    EmailNotConfirmed: HttpError(
        403, "email_not_confirmed", "Подтвердите email: ссылка в письме, которое мы отправили"
    ),
    AccountDisabled: HttpError(
        403, "account_disabled", "Учётная запись отключена. Обратитесь к администратору организации"
    ),
    SignInLocked: HttpError(
        429, "sign_in_locked", "Слишком много попыток входа. Попробуйте через 15 минут"
    ),
    NotSignedIn: HttpError(401, "not_signed_in", "Войдите в систему"),
}

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

Service = Annotated[AuthService, Depends(get_auth_service)]
AppSettings = Annotated[Settings, Depends(get_settings)]
AppClock = Annotated[Clock, Depends(get_clock)]


@router.post(
    "/email-confirmations", response_model=Me, status_code=200, responses=error_responses(400, 403)
)
async def confirm_email(
    body: EmailConfirmationRequest,
    response: Response,
    service: Service,
    settings: AppSettings,
    clock: AppClock,
) -> Me:
    """Confirm the email by the emailed link and sign the registrant in."""
    signed_in = await service.confirm_email(settings, clock, body.token)
    set_session_cookie(response, settings, signed_in.token)
    return signed_in.me


@router.post(
    "/sessions",
    response_model=Me,
    status_code=200,
    responses=error_responses(401, 403, 422, 429),
)
async def sign_in(
    body: SignInRequest,
    response: Response,
    service: Service,
    settings: AppSettings,
    clock: AppClock,
) -> Me:
    """Sign in with email and password."""
    signed_in = await service.sign_in(settings, clock, body)
    set_session_cookie(response, settings, signed_in.token)
    return signed_in.me


@router.delete("/sessions/current", status_code=204, responses=error_responses(401, 403))
async def sign_out(
    response: Response,
    service: Service,
    _context: Annotated[AuthContext, Depends(current_user)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    """End this browser's session."""
    # current_user has refused a missing cookie already; the cookie stays optional in the schema.
    if session_token is not None:
        await service.sign_out(session_token)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=Me, status_code=200, responses=error_responses(401))
async def read_me(
    service: Service,
    context: Annotated[AuthContext, Depends(current_user)],
) -> Me:
    """The signed-in user and their organization."""
    return await service.get_me(context)


@router.post("/password-resets", status_code=202, responses=error_responses(403, 422))
async def request_password_reset(
    body: PasswordResetRequest,
    service: Service,
    settings: AppSettings,
    clock: AppClock,
    mail: Annotated[MailSender, Depends(get_mail_sender)],
) -> Response:
    """Email a reset link; the answer is the same whether or not the email is registered."""
    await service.request_password_reset(settings, clock, mail, body.email)
    return Response(status_code=202)


@router.post("/password-resets/complete", status_code=204, responses=error_responses(400, 403, 422))
async def complete_password_reset(
    body: PasswordResetCompletion,
    service: Service,
    clock: AppClock,
) -> None:
    """Set a new password by the emailed link."""
    await service.complete_password_reset(clock, body.token, body.password)
