"""HTTP entry of correspondence: reply chains (`/api/v1/reply-chains`)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.modules.auth.dependencies import current_user
from app.modules.correspondence.schemas import ReplyChain, ReplyChainSummary
from app.modules.correspondence.service import CorrespondenceService, get_correspondence_service
from app.platform.auth_context import AuthContext
from app.platform.errors import HttpError, error_responses
from app.platform.pagination import (
    CURSOR_MAX_LENGTH,
    PAGE_DEFAULT_LIMIT,
    PAGE_MAX_LIMIT,
    InvalidCursor,
    Page,
)

# How each domain error of the module is answered over HTTP.
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    InvalidCursor: HttpError(400, "invalid_cursor", "Страница списка недействительна"),
}

router = APIRouter(prefix="/api/v1/reply-chains", tags=["reply-chains"])

Service = Annotated[CorrespondenceService, Depends(get_correspondence_service)]
Caller = Annotated[AuthContext, Depends(current_user)]


@router.get(
    "",
    response_model=Page[ReplyChainSummary],
    status_code=200,
    responses=error_responses(400, 401),
)
async def list_reply_chains(
    service: Service,
    context: Caller,
    limit: Annotated[int, Query(ge=1, le=PAGE_MAX_LIMIT)] = PAGE_DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=CURSOR_MAX_LENGTH)] = None,
) -> Page[ReplyChainSummary]:
    """The user's reply chains, the chain with the latest email first."""
    return await service.list_reply_chains(context, limit=limit, cursor=cursor)


@router.get(
    "/{chain_id}",
    response_model=ReplyChain,
    status_code=200,
    responses=error_responses(401, 404),
)
async def read_reply_chain(chain_id: UUID, service: Service, context: Caller) -> ReplyChain:
    """One reply chain with its emails, the oldest first."""
    return await service.get_reply_chain(context, chain_id)
