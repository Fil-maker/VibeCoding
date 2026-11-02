"""HTTP entry of projects (`/api/v1/projects`)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import current_user
from app.modules.projects.errors import ProjectExists
from app.modules.projects.schemas import ProjectCreate, ProjectSummary, ProjectTree
from app.modules.projects.service import ProjectsService, get_projects_service
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock, get_clock
from app.platform.errors import HttpError, error_responses
from app.platform.placement_engine import PlacementEngine, get_placement_engine

# How each domain error of the module is answered over HTTP.
ERROR_MAPPING: dict[type[Exception], HttpError] = {
    ProjectExists: HttpError(409, "project_exists", "Проект с таким названием уже есть"),
}

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

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
    """Fill the project from its description; a filled project is rebuilt."""
    return await service.fill(context, project_id, engine, clock)
