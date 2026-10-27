"""HTTP entry of invitations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.modules.auth.dependencies import current_admin, set_session_cookie
from app.modules.auth.schemas import Me
from app.modules.invitations.errors import (
    InvalidCursor,
    InvalidInvitation,
    InvitationExists,
    InvitationNotOpen,
)
from app.modules.invitations.schemas import (
    Invitation,
    InvitationAcceptance,
    InvitationPreview,
    InvitationRequest,
    InvitationToken,
)
from app.modules.invitations.service import InvitationsService, get_invitations_service
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock, get_clock
from app.platform.errors import HttpError, error_responses
from app.platform.mail import MailSender, get_mail_sender
from app.platform.pagination import CURSOR_MAX_LENGTH, PAGE_DEFAULT_LIMIT, PAGE_MAX_LIMIT, Page
from app.platform.settings import Settings, get_settings

# How each domain error of the module is answered over HTTP (`email_taken` is mapped by accounts).
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    InvalidInvitation: HttpError(
        400, "invalid_invitation", "Приглашение недействительно или устарело"
    ),
    InvalidCursor: HttpError(400, "invalid_cursor", "Некорректный курсор страницы"),
    InvitationExists: HttpError(
        409, "invitation_exists", "Приглашение на этот email уже отправлено"
    ),
    InvitationNotOpen: HttpError(
        409, "invitation_not_open", "Приглашение уже принято, отозвано или истекло"
    ),
}

router = APIRouter(prefix="/api/v1/invitations", tags=["invitations"])

Service = Annotated[InvitationsService, Depends(get_invitations_service)]
AppSettings = Annotated[Settings, Depends(get_settings)]
AppClock = Annotated[Clock, Depends(get_clock)]
Mail = Annotated[MailSender, Depends(get_mail_sender)]
Admin = Annotated[AuthContext, Depends(current_admin)]


@router.get("", response_model=Page[Invitation], responses=error_responses(400, 401, 404))
async def list_invitations(
    service: Service,
    clock: AppClock,
    context: Admin,
    limit: Annotated[int, Query(ge=1, le=PAGE_MAX_LIMIT)] = PAGE_DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=CURSOR_MAX_LENGTH)] = None,
) -> Page[Invitation]:
    """The organization's invitations, newest first."""
    return await service.list_invitations(clock, context, limit=limit, cursor=cursor)


@router.post(
    "",
    response_model=Invitation,
    status_code=201,
    responses=error_responses(401, 403, 404, 409, 422),
)
async def invite(
    body: InvitationRequest,
    service: Service,
    settings: AppSettings,
    clock: AppClock,
    mail: Mail,
    context: Admin,
) -> Invitation:
    """Invite an email to the organization; the status is `not_sent` when the mail failed."""
    return await service.invite(settings, clock, mail, context, body.email)


@router.post(
    "/preview",
    response_model=InvitationPreview,
    status_code=200,
    responses=error_responses(400, 403, 422),
)
async def preview_invitation(
    body: InvitationToken, service: Service, clock: AppClock
) -> InvitationPreview:
    """The organization and email behind an invitation link."""
    return await service.preview(clock, body.token)


@router.post(
    "/accept",
    response_model=Me,
    status_code=200,
    responses=error_responses(400, 403, 409, 422),
)
async def accept_invitation(
    body: InvitationAcceptance,
    response: Response,
    service: Service,
    settings: AppSettings,
    clock: AppClock,
) -> Me:
    """Join the organization by the invitation link and sign in."""
    signed_in = await service.accept(settings, clock, body)
    set_session_cookie(response, settings, signed_in.token)
    return signed_in.me


@router.post(
    "/{invitation_id}/resend",
    response_model=Invitation,
    status_code=200,
    responses=error_responses(401, 403, 404, 409),
)
async def resend_invitation(
    invitation_id: UUID,
    service: Service,
    settings: AppSettings,
    clock: AppClock,
    mail: Mail,
    context: Admin,
) -> Invitation:
    """Send an open invitation again with a new link."""
    return await service.resend(settings, clock, mail, context, invitation_id)


@router.post(
    "/{invitation_id}/revoke",
    response_model=Invitation,
    status_code=200,
    responses=error_responses(401, 403, 404),
)
async def revoke_invitation(
    invitation_id: UUID, service: Service, clock: AppClock, context: Admin
) -> Invitation:
    """Revoke an open invitation; one that is not open is returned unchanged."""
    return await service.revoke(clock, context, invitation_id)
