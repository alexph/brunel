from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from brunel.app import projects
from brunel.protocol import CreateProject, ProjectView

router = APIRouter()


def database(request: Request):
    if request.app.state.database is None:
        raise HTTPException(503, "Database unavailable")
    return request.app.state.database


def directory(value: str) -> str:
    try:
        return projects.canonical_directory(value)
    except (ValueError, OSError, RuntimeError) as error:
        raise HTTPException(422, str(error)) from error


@router.get("/projects", response_model=list[ProjectView])
async def list_projects(request: Request):
    return await run_in_threadpool(projects.list_projects, database(request))


@router.get("/projects/by-path", response_model=ProjectView)
async def project_by_path(request: Request, path: str):
    location = await run_in_threadpool(directory, path)
    project = await run_in_threadpool(projects.find_project, database(request), location)
    if project is None:
        raise HTTPException(404, "Project not registered")
    return project


@router.post("/projects", response_model=ProjectView)
async def create_project(request: Request, body: CreateProject):
    location = await run_in_threadpool(directory, body.location)
    project, created = await run_in_threadpool(projects.add_project, database(request), location)
    if created:
        request.app.state.daemon.project_created(project)
    return project
