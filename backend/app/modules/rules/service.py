"""Use cases of rules: list, create, change and delete; none of them moves a placement."""

from collections.abc import Awaitable, Callable, Collection, Sequence
from dataclasses import dataclass
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rules import repository
from app.modules.rules.domain import RULE_LIMIT, MatchRule, winning_rule
from app.modules.rules.errors import RuleExists, TooManyRules
from app.modules.rules.models import PlacementRule
from app.modules.rules.schemas import Rule, RuleCondition, RuleInput, RuleProject
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock
from app.platform.errors import NotFound

__all__ = [
    "MatchRule",
    "ProjectDirectory",
    "RulesService",
    "get_match_rule",
    "list_match_rules",
    "pick_winning_rule",
]

NamesOfProjects = Callable[[AsyncSession, UUID, Collection[UUID]], Awaitable[dict[UUID, str]]]
LockProjects = Callable[[AsyncSession, UUID], Awaitable[dict[UUID, str]]]


@dataclass(frozen=True)
class ProjectDirectory:
    """What rules need to know of the user's projects, handed in by the router.

    `names` returns `id -> name` of the given projects of the user; `lock_names` locks all the
    user's projects and returns them as `id -> name`.
    """

    names: NamesOfProjects
    lock_names: LockProjects


def _rule(rule: PlacementRule, project_name: str) -> Rule:
    return Rule(
        id=rule.id,
        condition=RuleCondition(rule.condition),
        value=rule.value,
        project=RuleProject(id=rule.project_id, name=project_name),
        thread_name=rule.thread_name,
    )


async def list_match_rules(session: AsyncSession, user_id: UUID) -> list[MatchRule]:
    """The user's rules for matching, in priority order; runs in the caller's transaction."""
    rows = await repository.list_rules_for_owner(session, user_id)
    return [
        MatchRule(
            id=row.id,
            condition=RuleCondition(row.condition),
            value=row.value,
            project_id=row.project_id,
            thread_name=row.thread_name,
            created_at=row.created_at,
        )
        for row in rows
    ]


async def get_match_rule(session: AsyncSession, user_id: UUID, rule_id: UUID) -> MatchRule | None:
    """The user's rule for matching, or `None` for an unknown or another user's id."""
    row = await repository.get_rule_for_owner(session, user_id, rule_id)
    if row is None:
        return None
    return MatchRule(
        id=row.id,
        condition=RuleCondition(row.condition),
        value=row.value,
        project_id=row.project_id,
        thread_name=row.thread_name,
        created_at=row.created_at,
    )


async def count_rules_targeting(session: AsyncSession, user_id: UUID, project_id: UUID) -> int:
    """How many of the user's rules lead into the project; runs in the caller's transaction."""
    return await repository.count_rules_targeting_for_owner(session, user_id, project_id)


def pick_winning_rule(
    rules: Sequence[MatchRule], senders: Sequence[str], subject: str
) -> MatchRule | None:
    """The rule that places a chain with these senders and subject, or `None`."""
    return winning_rule(rules, senders, subject)


class RulesService:
    """The user-facing use cases of rules bound to one database session.

    A write that adds or retargets a rule locks the user's projects (through the project
    directory) before it counts the rules or checks the target project, so two parallel creates
    cannot both pass the limit. It moves no placement.
    """

    def __init__(self, session: AsyncSession, projects: ProjectDirectory) -> None:
        self._session = session
        self._projects = projects

    async def list_rules(self, context: AuthContext) -> list[Rule]:
        """The user's rules in the order they win."""
        user_id = context.user_id
        async with self._session.begin():
            rows = await repository.list_rules_for_owner(self._session, user_id)
            names = await self._projects.names(
                self._session, user_id, {row.project_id for row in rows}
            )
        return [_rule(row, names[row.project_id]) for row in rows]

    async def create(self, context: AuthContext, clock: Clock, body: RuleInput) -> Rule:
        """Create a rule; `NotFound` for a project that is not the user's.

        Raises `RuleExists` for a repeat (also when the unique index is hit in a race) and
        `TooManyRules` at the limit.
        """
        user_id = context.user_id
        now = clock.now()
        try:
            async with self._session.begin():
                names = await self._projects.lock_names(self._session, user_id)
                project_name = names.get(body.project_id)
                if project_name is None:
                    raise NotFound
                if await repository.count_rules_for_owner(self._session, user_id) >= RULE_LIMIT:
                    raise TooManyRules
                if await repository.has_rule_for_owner(
                    self._session,
                    user_id,
                    condition=body.condition,
                    value=body.value,
                    except_rule_id=None,
                ):
                    raise RuleExists
                rule = await repository.add_rule_for_owner(
                    self._session,
                    user_id,
                    condition=body.condition,
                    value=body.value,
                    project_id=body.project_id,
                    thread_name=body.thread_name,
                    now=now,
                )
        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                raise RuleExists from e
            raise
        return _rule(rule, project_name)

    async def update(
        self, context: AuthContext, clock: Clock, rule_id: UUID, body: RuleInput
    ) -> Rule:
        """Replace every part of the user's rule; the same errors as `create`, but no limit."""
        user_id = context.user_id
        try:
            async with self._session.begin():
                rule = await repository.get_rule_for_owner(self._session, user_id, rule_id)
                names = await self._projects.lock_names(self._session, user_id)
                project_name = names.get(body.project_id)
                if rule is None or project_name is None:
                    raise NotFound
                if await repository.has_rule_for_owner(
                    self._session,
                    user_id,
                    condition=body.condition,
                    value=body.value,
                    except_rule_id=rule.id,
                ):
                    raise RuleExists
                rule.condition = body.condition
                rule.value = body.value
                rule.project_id = body.project_id
                rule.thread_name = body.thread_name
                rule.updated_at = clock.now()
                await self._session.flush()
        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                raise RuleExists from e
            raise
        return _rule(rule, project_name)

    async def delete(self, context: AuthContext, rule_id: UUID) -> None:
        """Delete the user's rule; `NotFound` for another user's or an unknown id."""
        async with self._session.begin():
            rule = await repository.get_rule_for_owner(self._session, context.user_id, rule_id)
            if rule is None:
                raise NotFound
            await repository.delete_rule_for_owner(self._session, context.user_id, rule_id)
