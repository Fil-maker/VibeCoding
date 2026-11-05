"""HTTP entry of attachments (`/api/v1/emails/{email_id}/attachments/{index}`)."""

from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, Response

from app.modules.attachments.errors import (
    AttachmentEmailGone,
    AttachmentMailboxDisconnected,
    AttachmentServerUnreachable,
    AttachmentSignInFailed,
)
from app.modules.attachments.service import download_attachment
from app.modules.auth.dependencies import current_user
from app.platform.auth_context import AuthContext
from app.platform.db import Database
from app.platform.errors import HttpError, error_responses
from app.platform.mail_reader import MailReader, get_mail_reader
from app.platform.secret_box import SecretBox, get_secret_box
from app.platform.settings import Settings, get_settings

# How each domain error of the module is answered over HTTP.
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    AttachmentMailboxDisconnected: HttpError(
        409, "mailbox_disconnected", "Файл недоступен: ящик отключён"
    ),
    AttachmentEmailGone: HttpError(410, "email_gone", "Письмо больше не найдено в ящике"),
    AttachmentSignInFailed: HttpError(
        502, "mailbox_sign_in_failed", "Не удалось получить файл: не удалось войти в ящик"
    ),
    AttachmentServerUnreachable: HttpError(
        504, "mailbox_unreachable", "Не удалось получить файл: сервер не отвечает"
    ),
}

router = APIRouter(prefix="/api/v1/emails", tags=["attachments"])

Caller = Annotated[AuthContext, Depends(current_user)]


def _database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


@router.get(
    "/{email_id}/attachments/{index}",
    response_class=Response,
    status_code=200,
    responses={
        200: {
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            }
        },
        **error_responses(401, 404, 409, 410, 502, 504),
    },
)
async def download(
    email_id: UUID,
    index: Annotated[int, Path(ge=0)],
    context: Caller,
    database: Annotated[Database, Depends(_database)],
    reader: Annotated[MailReader, Depends(get_mail_reader)],
    settings: Annotated[Settings, Depends(get_settings)],
    secret_box: Annotated[SecretBox, Depends(get_secret_box)],
) -> Response:
    """The file of one attachment, fetched from the mailbox; always offered for saving."""
    file = await download_attachment(
        database, reader, settings, secret_box, context, email_id, index
    )
    return Response(
        content=file.content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file.name, safe='')}",
            "X-Content-Type-Options": "nosniff",
        },
    )
