"""HTTP entry of mailboxes (`/api/v1/mailboxes`)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.modules.auth.dependencies import current_user
from app.modules.mailboxes.errors import (
    MailboxExists,
    MailboxServerUnreachable,
    MailboxSignInRefused,
)
from app.modules.mailboxes.schemas import Mailbox, MailboxConnect
from app.modules.mailboxes.service import MailboxesService, get_mailboxes_service
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock, get_clock
from app.platform.errors import (
    ErrorBody,
    ErrorResponse,
    HttpError,
    error_responses,
    register_domain_errors,
)
from app.platform.mail_reader import MailReader, get_mail_reader
from app.platform.secret_box import SecretBox, get_secret_box
from app.platform.settings import Settings, get_settings

UNREACHABLE_STATUS = 422

# How each domain error of the module is answered over HTTP.
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    MailboxExists: HttpError(409, "mailbox_exists", "Этот ящик уже подключён"),
    MailboxSignInRefused: HttpError(
        422,
        "mailbox_sign_in_failed",
        "Не удалось войти в ящик: проверьте логин и пароль приложения",
    ),
}

router = APIRouter(prefix="/api/v1/mailboxes", tags=["mailboxes"])

Service = Annotated[MailboxesService, Depends(get_mailboxes_service)]
Caller = Annotated[AuthContext, Depends(current_user)]
ClockDep = Annotated[Clock, Depends(get_clock)]


async def _answer_unreachable(_request: Request, exc: Exception) -> JSONResponse:
    # The message names the server, so it cannot sit in the static `ERROR_MAPPING`.
    if not isinstance(exc, MailboxServerUnreachable):
        raise TypeError("handler registered for another exception type")
    body = ErrorBody(
        code="mailbox_unreachable", message=f"Не удалось подключиться к серверу {exc.server}"
    )
    payload = ErrorResponse(error=body).model_dump(exclude_none=True)
    return JSONResponse(status_code=UNREACHABLE_STATUS, content=payload)


def register_mailbox_errors(app: FastAPI) -> None:
    """Answer every domain error of the module with its HTTP error."""
    register_domain_errors(app, ERROR_MAPPING)
    app.add_exception_handler(MailboxServerUnreachable, _answer_unreachable)


@router.get("", response_model=list[Mailbox], status_code=200, responses=error_responses(401))
async def list_mailboxes(service: Service, context: Caller) -> list[Mailbox]:
    """The user's connected mailboxes."""
    return await service.list_mailboxes(context)


@router.post(
    "",
    response_model=Mailbox,
    status_code=201,
    responses=error_responses(401, 403, 409, 422),
)
async def connect_mailbox(
    body: MailboxConnect,
    service: Service,
    context: Caller,
    reader: Annotated[MailReader, Depends(get_mail_reader)],
    secret_box: Annotated[SecretBox, Depends(get_secret_box)],
    clock: ClockDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Mailbox:
    """Check the sign-in, then save the mailbox; it is read soon after."""
    return await service.connect(context, reader, secret_box, clock, settings, body)


@router.post(
    "/{mailbox_id}/refresh",
    response_model=Mailbox,
    status_code=202,
    responses=error_responses(401, 403, 404),
)
async def refresh_mailbox(
    mailbox_id: UUID, service: Service, context: Caller, clock: ClockDep
) -> Mailbox:
    """Ask for a read of the mailbox at the next tick."""
    return await service.refresh(context, mailbox_id, clock)


@router.delete(
    "/{mailbox_id}",
    status_code=204,
    responses=error_responses(401, 403, 404),
)
async def disconnect_mailbox(
    mailbox_id: UUID, service: Service, context: Caller, clock: ClockDep
) -> Response:
    """Delete the password and stop reading; the read emails stay."""
    await service.disconnect(context, mailbox_id, clock)
    return Response(status_code=204)
