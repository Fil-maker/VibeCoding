"""HTTP entry of accounts: registration (`/api/v1/auth`)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.accounts.errors import EmailTaken
from app.modules.accounts.schemas import RegistrationRequest, RegistrationResult
from app.modules.accounts.service import AccountsService, get_accounts_service
from app.platform.clock import Clock, get_clock
from app.platform.errors import HttpError, error_responses
from app.platform.mail import MailSender, get_mail_sender
from app.platform.settings import Settings, get_settings

# How each domain error of the module is answered over HTTP.
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    EmailTaken: HttpError(409, "email_taken", "Этот email уже зарегистрирован"),
}

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

Service = Annotated[AccountsService, Depends(get_accounts_service)]


@router.post(
    "/registrations",
    response_model=RegistrationResult,
    status_code=201,
    responses=error_responses(403, 409, 422),
)
async def register(
    body: RegistrationRequest,
    service: Service,
    settings: Annotated[Settings, Depends(get_settings)],
    clock: Annotated[Clock, Depends(get_clock)],
    mail: Annotated[MailSender, Depends(get_mail_sender)],
) -> RegistrationResult:
    """Register a user; a confirmation email follows."""
    return await service.register(settings, clock, mail, body)
