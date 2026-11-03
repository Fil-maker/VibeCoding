"""Request and response models of projects: the list, the tree and the placement of a chain."""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, ValidationInfo, model_validator
from pydantic_core import PydanticCustomError

from app.modules.rules.schemas import RuleCondition
from app.platform.errors import FIELD_MESSAGE_TYPE
from app.platform.validation import RequestModel

NAME_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 2000
NAME_EMPTY_MESSAGE = "Укажите название проекта"
NAME_LONG_MESSAGE = "Название — не длиннее 100 символов"
DESCRIPTION_EMPTY_MESSAGE = "Опишите проект"
DESCRIPTION_LONG_MESSAGE = "Описание — не длиннее 2000 символов"
THREAD_NAME_EMPTY_MESSAGE = "Укажите название ветки"
THREAD_NAME_LONG_MESSAGE = "Название ветки — не длиннее 100 символов"
THREAD_CHOICE_MESSAGE = "Выберите либо ветку, либо новую ветку"
TEXT_FIELDS = ("name", "description")


def _fail(message: str) -> PydanticCustomError:
    return PydanticCustomError(FIELD_MESSAGE_TYPE, "{message}", {"message": message})


def _check_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise _fail(NAME_EMPTY_MESSAGE)
    if len(name) > NAME_MAX_LENGTH:
        raise _fail(NAME_LONG_MESSAGE)
    return name


def _check_description(value: str) -> str:
    description = value.strip()
    if not description:
        raise _fail(DESCRIPTION_EMPTY_MESSAGE)
    if len(description) > DESCRIPTION_MAX_LENGTH:
        raise _fail(DESCRIPTION_LONG_MESSAGE)
    return description


class ProjectCreate(RequestModel):
    """The form «Новый проект»."""

    name: Annotated[str, AfterValidator(_check_name)]
    description: Annotated[str, AfterValidator(_check_description)]

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


class ProjectSummary(BaseModel):
    """A row of the list of projects."""

    id: UUID
    name: str
    filled: bool
    placed_count: int
    unassigned_count: int


class PlacementRuleRef(BaseModel):
    """The rule as it was when it placed a chain."""

    condition: RuleCondition
    value: str


class Placement(BaseModel):
    """How a chain got where it is.

    The version and similarity are set exactly for `engine`, `rule` exactly for `rule`.
    """

    kind: Literal["engine", "manual", "rule"]
    engine_version: str | None
    similarity: float | None
    rule: PlacementRuleRef | None


class PlacedChain(BaseModel):
    """A chain in a tree with the reason for its place."""

    id: UUID
    subject: str
    email_count: int
    latest_email_at: datetime
    placement: Placement


class ThreadNode(BaseModel):
    """A thread of a project with the chains of one counterparty in it."""

    id: UUID
    name: str
    chains: list[PlacedChain]


class CounterpartyNode(BaseModel):
    """A counterparty of a project; a null `address` is «Без контрагента»."""

    address: str | None
    name: str
    threads: list[ThreadNode]


class ProjectTree(BaseModel):
    """A project page: its description, the tree and «Неразобранное»."""

    id: UUID
    name: str
    description: str
    filled: bool
    counterparties: list[CounterpartyNode]
    unassigned: list[PlacedChain]


class ThreadSummary(BaseModel):
    """A thread of a project."""

    id: UUID
    name: str


class ProjectRef(BaseModel):
    """A project a chain is in."""

    id: UUID
    name: str


class ChainLocation(BaseModel):
    """Where a chain is: `project` and `placement` are set exactly when `state` is «placed»."""

    state: Literal["placed", "none", "excluded"]
    project: ProjectRef | None
    thread: ThreadSummary | None
    placement: Placement | None


def _check_thread_name(value: str | None, info: ValidationInfo) -> str | None:
    if value is None:
        return None
    if info.data.get("thread_id") is not None:
        raise _fail(THREAD_CHOICE_MESSAGE)
    name = value.strip()
    if not name:
        raise _fail(THREAD_NAME_EMPTY_MESSAGE)
    if len(name) > NAME_MAX_LENGTH:
        raise _fail(THREAD_NAME_LONG_MESSAGE)
    return name


class PlacementMove(RequestModel):
    """Where to put a chain: a thread, a new thread, or «Неразобранное» when both are null."""

    project_id: UUID
    thread_id: UUID | None = None
    new_thread_name: Annotated[str | None, AfterValidator(_check_thread_name)] = None


class RuleMoveSource(BaseModel):
    """Where a chain is before a rule moves it: in no project, or in a project (and a thread)."""

    state: Literal["none", "placed"]
    project: ProjectRef | None
    thread: ThreadSummary | None


class RuleMoveTarget(BaseModel):
    """Where the rule puts a chain; a null `thread_name` is «Неразобранное»."""

    project: ProjectRef
    thread_name: str | None


class RuleMove(BaseModel):
    """A chain a rule would move, with where it is and where it goes."""

    chain_id: UUID
    subject: str
    latest_email_at: datetime
    current: RuleMoveSource
    target: RuleMoveTarget


class RuleMoves(BaseModel):
    """The chains a rule would move, newest first."""

    moves: list[RuleMove]


class RuleApply(RequestModel):
    """The chains the user saw in the list; duplicates are ignored."""

    chain_ids: Annotated[list[UUID], Field(max_length=5000)]


class RuleApplied(BaseModel):
    """How many chains an applied rule moved."""

    moved: int
