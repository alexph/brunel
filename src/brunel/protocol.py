from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

PROTOCOL_VERSION = 2


class DaemonStatus(BaseModel):
    protocol_version: int = PROTOCOL_VERSION
    run_id: str
    pid: int
    mode: Literal["on-demand", "service"]
    clients: int
    live_work: int
    idle_timeout: float


class StatusEvent(BaseModel):
    type: Literal["snapshot", "daemon.status"]
    sequence: int
    payload: DaemonStatus


class ProjectView(BaseModel):
    id: int
    name: str
    location: str


class CreateProject(BaseModel):
    location: str


class ProjectEvent(BaseModel):
    type: Literal["project.created"] = "project.created"
    sequence: int
    payload: ProjectView


Event = Annotated[StatusEvent | ProjectEvent, Field(discriminator="type")]
event_adapter = TypeAdapter(Event)
