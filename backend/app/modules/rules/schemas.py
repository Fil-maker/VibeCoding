"""Request and response models of rules: the form, its checks and normalisation, the list row."""

import re
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from app.platform.errors import FIELD_MESSAGE_TYPE
from app.platform.validation import EMAIL_MAX_LENGTH, RequestModel

SUBJECT_MAX_LENGTH = 200
THREAD_NAME_MAX_LENGTH = 100
DOMAIN_MAX_LENGTH = 253
DOMAIN_MIN_LABELS = 2
ADDRESS_MESSAGE = "Укажите адрес почты"
DOMAIN_MESSAGE = "Укажите домен, например stroymaster.example"
SUBJECT_EMPTY_MESSAGE = "Укажите слова темы"
SUBJECT_LONG_MESSAGE = "Слова темы — не длиннее 200 символов"
THREAD_NAME_LONG_MESSAGE = "Название ветки — не длиннее 100 символов"
PROJECT_MESSAGE = "Выберите проект"
_SPACES = re.compile(r"\s+")


class RuleCondition(StrEnum):
    """What a rule looks at in a chain."""

    ADDRESS = "address"
    DOMAIN = "domain"
    SUBJECT = "subject"


def _fail(message: str) -> PydanticCustomError:
    return PydanticCustomError(FIELD_MESSAGE_TYPE, "{message}", {"message": message})


def _check_project_id(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            pass
    raise _fail(PROJECT_MESSAGE)


def _check_thread_name(value: str | None) -> str | None:
    if value is None:
        return None
    name = value.strip()
    if len(name) > THREAD_NAME_MAX_LENGTH:
        raise _fail(THREAD_NAME_LONG_MESSAGE)
    return name or None


def _normal_address(value: str) -> str:
    address = value.strip().lower()
    local, separator, host = address.partition("@")
    if (
        not separator
        or not local
        or not host
        or "@" in host
        or _SPACES.search(address)
        or len(address) > EMAIL_MAX_LENGTH
    ):
        raise _fail(ADDRESS_MESSAGE)
    return address


def _normal_domain(value: str) -> str:
    domain = value.strip().lower()
    labels = domain.split(".")
    valid = len(labels) >= DOMAIN_MIN_LABELS and len(domain) <= DOMAIN_MAX_LENGTH
    valid = valid and all(label and all(c.isalnum() or c == "-" for c in label) for label in labels)
    if not valid:
        raise _fail(DOMAIN_MESSAGE)
    return domain


def _normal_subject(value: str) -> str:
    words = _SPACES.sub(" ", value.strip())
    if not words:
        raise _fail(SUBJECT_EMPTY_MESSAGE)
    if len(words) > SUBJECT_MAX_LENGTH:
        raise _fail(SUBJECT_LONG_MESSAGE)
    return words


class RuleInput(RequestModel):
    """The form of a rule; a rule is created and replaced by the same body."""

    condition: RuleCondition
    value: str
    project_id: Annotated[UUID, BeforeValidator(_check_project_id)]
    thread_name: Annotated[str | None, AfterValidator(_check_thread_name)] = None

    @model_validator(mode="before")
    @classmethod
    def _blank_missing_fields(cls, data: Any) -> Any:  # pyright: ignore[reportAny] -- pydantic hands over the raw body
        """A missing or non-text value or project gets the same message as an empty one."""
        if not isinstance(data, dict):
            return data  # pyright: ignore[reportUnknownVariableType] -- the raw body
        filled: dict[Any, Any] = dict(data)  # pyright: ignore[reportUnknownArgumentType] -- the raw body
        if not isinstance(filled.get("value"), str):
            filled["value"] = ""
        filled.setdefault("project_id", "")
        return filled

    @field_validator("value")
    @classmethod
    def _normalise_value(cls, value: str, info: ValidationInfo) -> str:
        condition = info.data.get("condition")
        if condition is RuleCondition.ADDRESS:
            return _normal_address(value)
        if condition is RuleCondition.DOMAIN:
            return _normal_domain(value)
        if condition is RuleCondition.SUBJECT:
            return _normal_subject(value)
        return value


class RuleProject(BaseModel):
    """The target project of a rule."""

    id: UUID
    name: str


class Rule(BaseModel):
    """A rule of the list; a null `thread_name` is «Неразобранное»."""

    id: UUID
    condition: RuleCondition
    value: str
    project: RuleProject
    thread_name: str | None
