"""HTTP entry of rules (`/api/v1/rules`)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import current_user
from app.modules.projects.service import list_project_names, lock_project_names
from app.modules.rules.domain import RULE_LIMIT
from app.modules.rules.errors import RuleExists, TooManyRules
from app.modules.rules.schemas import Rule, RuleInput
from app.modules.rules.service import ProjectDirectory, RulesService
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock, get_clock
from app.platform.db import get_database_session
from app.platform.errors import HttpError, error_responses

# How each domain error of the module is answered over HTTP.
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    RuleExists: HttpError(409, "rule_exists", "Такое правило уже есть"),
    TooManyRules: HttpError(409, "too_many_rules", f"Правил не может быть больше {RULE_LIMIT}"),
}

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


def get_rules_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> RulesService:
    """Dependency factory of the rules use cases."""
    return RulesService(
        session, ProjectDirectory(names=list_project_names, lock_names=lock_project_names)
    )


Service = Annotated[RulesService, Depends(get_rules_service)]
Caller = Annotated[AuthContext, Depends(current_user)]
ClockDep = Annotated[Clock, Depends(get_clock)]


@router.get("", response_model=list[Rule], status_code=200, responses=error_responses(401))
async def list_rules(service: Service, context: Caller) -> list[Rule]:
    """The user's rules in the order they win."""
    return await service.list_rules(context)


@router.post(
    "",
    response_model=Rule,
    status_code=201,
    responses=error_responses(401, 403, 404, 409, 422),
)
async def create_rule(body: RuleInput, service: Service, context: Caller, clock: ClockDep) -> Rule:
    """Create a rule."""
    return await service.create(context, clock, body)


@router.put(
    "/{rule_id}",
    response_model=Rule,
    status_code=200,
    responses=error_responses(401, 403, 404, 409, 422),
)
async def update_rule(
    rule_id: UUID, body: RuleInput, service: Service, context: Caller, clock: ClockDep
) -> Rule:
    """Change a rule."""
    return await service.update(context, clock, rule_id, body)


@router.delete(
    "/{rule_id}",
    status_code=204,
    response_class=Response,
    responses=error_responses(401, 403, 404),
)
async def delete_rule(rule_id: UUID, service: Service, context: Caller) -> None:
    """Delete a rule; the chains it placed stay where they are."""
    await service.delete(context, rule_id)
