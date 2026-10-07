from typing import Literal

from pydantic import BaseModel

PROTOCOL_VERSION = 1


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
