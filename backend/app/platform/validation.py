"""Request-model building blocks: strict base class and the shared, Russian-worded field types."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints
from pydantic_core import PydanticCustomError

from app.platform.errors import FIELD_MESSAGE_TYPE, FIELD_MESSAGES

NAME_MAX_LENGTH = 200
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128
SIGN_IN_PASSWORD_MAX_LENGTH = 1024
TOKEN_MAX_LENGTH = 512
EMPTY_CREDENTIALS_MESSAGE = "Укажите email и пароль"


class RequestModel(BaseModel):
    """Base of request bodies: an unknown field, such as `organization_id`, is refused."""

    model_config = ConfigDict(extra="forbid")


def _fail(message: str) -> PydanticCustomError:
    return PydanticCustomError(FIELD_MESSAGE_TYPE, "{message}", {"message": message})


def normalize_email(value: str) -> str:
    """Trim and lower-case an email; the stored and compared form."""
    return value.strip().lower()


def _text(message: str) -> AfterValidator:
    def check(value: str) -> str:
        stripped = value.strip()
        if not 1 <= len(stripped) <= NAME_MAX_LENGTH:
            raise _fail(message)
        return stripped

    return AfterValidator(check)


def _check_email(value: str) -> str:
    email = normalize_email(value)
    local, separator, domain = email.partition("@")
    if not separator or not local or not domain or "@" in domain or len(email) > EMAIL_MAX_LENGTH:
        raise _fail(FIELD_MESSAGES["email"])
    return email


def _check_password(value: str) -> str:
    if not PASSWORD_MIN_LENGTH <= len(value) <= PASSWORD_MAX_LENGTH:
        raise _fail(FIELD_MESSAGES["password"])
    return value


def _check_sign_in_email(value: str) -> str:
    email = normalize_email(value)
    if not email or len(email) > EMAIL_MAX_LENGTH:
        raise _fail(EMPTY_CREDENTIALS_MESSAGE)
    return email


def _check_sign_in_password(value: str) -> str:
    if not value or len(value) > SIGN_IN_PASSWORD_MAX_LENGTH:
        raise _fail(EMPTY_CREDENTIALS_MESSAGE)
    return value


OrganizationName = Annotated[str, _text(FIELD_MESSAGES["organization_name"])]
PersonName = Annotated[str, _text(FIELD_MESSAGES["name"])]
EmailAddress = Annotated[str, AfterValidator(_check_email)]
NewPassword = Annotated[str, AfterValidator(_check_password)]
SignInEmail = Annotated[str, AfterValidator(_check_sign_in_email)]
SignInPassword = Annotated[str, AfterValidator(_check_sign_in_password)]
LinkToken = Annotated[str, StringConstraints(max_length=TOKEN_MAX_LENGTH)]
