"""HTTP entry of projects (`/api/v1/projects`)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import current_user
from app.modules.projects.errors import ChainNotInProject, ProjectExists
from app.modules.projects.schemas import (
    ChainLocation,
    PlacementMove,
    ProjectCreate,
    ProjectSummary,
    ProjectTree,
    ThreadSummary,
)
from app.modules.projects.service import ProjectsService, get_projects_service
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock, get_clock
from app.platform.errors import HttpError, error_responses
from app.platform.placement_engine import PlacementEngine, get_placement_engine

# How each domain error of the module is answered over HTTP.
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    ProjectExists: HttpError(409, "project_exists", "Проект с таким названием уже есть"),
    ChainNotInProject: HttpError(409, "chain_not_in_project", "Цепочка не входит ни в один проект"),
}

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])
placements_router = APIRouter(prefix="/api/v1/placements", tags=["projects"])

Service = Annotated[ProjectsService, Depends(get_projects_service)]
Caller = Annotated[AuthContext, Depends(current_user)]
ClockDep = Annotated[Clock, Depends(get_clock)]


@router.get(
    "", response_model=list[ProjectSummary], status_code=200, responses=error_responses(401)
)
async def list_projects(service: Service, context: Caller) -> list[ProjectSummary]:
    """The user's projects by name."""
    return await service.list_projects(context)


@router.post(
    "",
    response_model=ProjectSummary,
    status_code=201,
    responses=error_responses(401, 403, 409, 422),
)
async def create_project(
    body: ProjectCreate, service: Service, context: Caller, clock: ClockDep
) -> ProjectSummary:
    """Create an empty project."""
    return await service.create(context, clock, body)


@router.get(
    "/{project_id}",
    response_model=ProjectTree,
    status_code=200,
    responses=error_responses(401, 404),
)
async def read_project(project_id: UUID, service: Service, context: Caller) -> ProjectTree:
    """A project with its tree."""
    return await service.get_tree(context, project_id)


@router.post(
    "/{project_id}/fill",
    response_model=ProjectTree,
    status_code=200,
    responses=error_responses(401, 403, 404),
)
async def fill_project(
    project_id: UUID,
    service: Service,
    context: Caller,
    engine: Annotated[PlacementEngine, Depends(get_placement_engine)],
    clock: ClockDep,
) -> ProjectTree:
    """Fill the project from its description; a filled project is rebuilt, hand placements stay."""
    return await service.fill(context, project_id, engine, clock)


@router.get(
    "/{project_id}/threads",
    response_model=list[ThreadSummary],
    status_code=200,
    responses=error_responses(401, 404),
)
async def list_project_threads(
    project_id: UUID, service: Service, context: Caller
) -> list[ThreadSummary]:
    """The threads of a project in order."""
    return await service.list_threads(context, project_id)


@placements_router.get(
    "/{chain_id}",
    response_model=ChainLocation,
    status_code=200,
    responses=error_responses(401, 404),
)
async def read_placement(chain_id: UUID, service: Service, context: Caller) -> ChainLocation:
    """Where a chain is."""
    return await service.get_location(context, chain_id)


@placements_router.put(
    "/{chain_id}",
    response_model=ChainLocation,
    status_code=200,
    responses=error_responses(401, 403, 404, 422),
)
async def move_placement(
    chain_id: UUID, body: PlacementMove, service: Service, context: Caller, clock: ClockDep
) -> ChainLocation:
    """Place a chain by hand into a thread, a new thread or «Неразобранное» of a project."""
    return await service.move_chain(context, clock, chain_id, body)


@placements_router.delete(
    "/{chain_id}",
    response_model=ChainLocation,
    status_code=200,
    responses=error_responses(401, 403, 404, 409),
)
async def take_chain_out(
    chain_id: UUID, service: Service, context: Caller, clock: ClockDep
) -> ChainLocation:
    """Take a chain out of its project for good."""
    return await service.take_chain_out(context, clock, chain_id)
