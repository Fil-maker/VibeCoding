"""Request and response models of mailboxes. The password is accepted, never returned."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import AfterValidator, BaseModel, model_validator
from pydantic_core import PydanticCustomError

from app.modules.mailboxes.models import LOGIN_MAX_LENGTH, SERVER_MAX_LENGTH, MailboxStatus
from app.platform.errors import FIELD_MESSAGE_TYPE
from app.platform.validation import RequestModel

PASSWORD_MAX_LENGTH = 256
DEFAULT_IMAP_PORT = 993
PORT_MIN = 1
PORT_MAX = 65535
SERVER_MESSAGE = "Укажите сервер IMAP"
LOGIN_MESSAGE = "Укажите логин"
PASSWORD_MESSAGE = "Укажите пароль приложения"
PORT_MESSAGE = "Порт должен быть от 1 до 65535"
TEXT_FIELDS = ("server", "login", "password")


def _fail(message: str) -> PydanticCustomError:
    return PydanticCustomError(FIELD_MESSAGE_TYPE, "{message}", {"message": message})


def _check_server(value: str) -> str:
    server = value.strip().lower()
    if not 1 <= len(server) <= SERVER_MAX_LENGTH:
        raise _fail(SERVER_MESSAGE)
    return server


def _check_login(value: str) -> str:
    login = value.strip()
    if not 1 <= len(login) <= LOGIN_MAX_LENGTH:
        raise _fail(LOGIN_MESSAGE)
    return login


def _check_password(value: str) -> str:
    if not 1 <= len(value) <= PASSWORD_MAX_LENGTH:
        raise _fail(PASSWORD_MESSAGE)
    return value


def _check_port(value: int) -> int:
    if not PORT_MIN <= value <= PORT_MAX:
        raise _fail(PORT_MESSAGE)
    return value


class MailboxConnect(RequestModel):
    """The form «Подключить ящик»."""

    server: Annotated[str, AfterValidator(_check_server)]
    port: Annotated[int, AfterValidator(_check_port)] = DEFAULT_IMAP_PORT
    login: Annotated[str, AfterValidator(_check_login)]
    password: Annotated[str, AfterValidator(_check_password)]

    @model_validator(mode="before")
    @classmethod
    def _blank_missing_texts(cls, data: Any) -> Any:  # pyright: ignore[reportAny] -- pydantic hands over the raw body
        """A missing or non-text field gets the same «Укажите …» message as an empty one."""
        if not isinstance(data, dict):
            return data  # pyright: ignore[reportUnknownVariableType] -- the raw body
        filled: dict[Any, Any] = dict(data)  # pyright: ignore[reportUnknownArgumentType] -- the raw body
        for name in TEXT_FIELDS:
            if not isinstance(filled.get(name), str):
                filled[name] = ""
        return filled


class Mailbox(BaseModel):
    """A connected mailbox as the list shows it."""

    id: UUID
    server: str
    port: int
    login: str
    status: MailboxStatus
    error: str | None
    last_read_at: datetime | None
