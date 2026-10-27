"""HTTP entry of accounts: registration (`/api/v1/auth`) and the members of an organization.

The members routes (`/api/v1/members`) are for administrators only.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.modules.accounts.errors import (
    CannotDeactivateSelf,
    EmailTaken,
    InvalidCursor,
    LastAdministrator,
    MemberInactive,
    MemberNotFound,
)
from app.modules.accounts.schemas import Member, RegistrationRequest, RegistrationResult, RoleChange
from app.modules.accounts.service import AccountsService, get_accounts_service
from app.modules.auth.dependencies import current_admin
from app.platform.auth_context import AuthContext, Role
from app.platform.clock import Clock, get_clock
from app.platform.errors import NOT_FOUND, HttpError, error_responses
from app.platform.mail import MailSender, get_mail_sender
from app.platform.pagination import CURSOR_MAX_LENGTH, PAGE_DEFAULT_LIMIT, PAGE_MAX_LIMIT, Page
from app.platform.settings import Settings, get_settings

# How each domain error of the module is answered over HTTP.
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    EmailTaken: HttpError(409, "email_taken", "Этот email уже зарегистрирован"),
    MemberNotFound: NOT_FOUND,
    InvalidCursor: HttpError(400, "invalid_cursor", "Некорректный курсор страницы"),
    CannotDeactivateSelf: HttpError(
        409, "cannot_deactivate_self", "Нельзя отключить свою учётную запись"
    ),
    LastAdministrator: HttpError(
        409,
        "last_administrator",
        "В организации должен остаться хотя бы один активный администратор",
    ),
    MemberInactive: HttpError(409, "member_inactive", "Сначала включите учётную запись участника"),
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
    """Register an organization and its first administrator; a confirmation email follows."""
    return await service.register_organization(settings, clock, mail, body)


members_router = APIRouter(prefix="/api/v1/members", tags=["members"])

Admin = Annotated[AuthContext, Depends(current_admin)]


@members_router.get("", response_model=Page[Member], responses=error_responses(400, 401, 404))
async def list_members(
    service: Service,
    context: Admin,
    limit: Annotated[int, Query(ge=1, le=PAGE_MAX_LIMIT)] = PAGE_DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=CURSOR_MAX_LENGTH)] = None,
) -> Page[Member]:
    """The confirmed members of the organization, ordered by name."""
    return await service.list_members(context, limit=limit, cursor=cursor)


@members_router.post(
    "/{member_id}/deactivate",
    response_model=Member,
    status_code=200,
    responses=error_responses(401, 403, 404, 409),
)
async def deactivate_member(member_id: UUID, service: Service, context: Admin) -> Member:
    """Deactivate a member; their sessions end at once."""
    return await service.deactivate_member(context, member_id)


@members_router.post(
    "/{member_id}/reactivate",
    response_model=Member,
    status_code=200,
    responses=error_responses(401, 403, 404),
)
async def reactivate_member(member_id: UUID, service: Service, context: Admin) -> Member:
    """Reactivate a deactivated member."""
    return await service.reactivate_member(context, member_id)


@members_router.put(
    "/{member_id}/role",
    response_model=Member,
    status_code=200,
    responses=error_responses(401, 403, 404, 409, 422),
)
async def change_member_role(
    member_id: UUID, body: RoleChange, service: Service, context: Admin
) -> Member:
    """Change the role of a member; it applies to their next request."""
    return await service.change_role(context, member_id, Role(body.role))
