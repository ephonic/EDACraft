"""
Pydantic schemas for API request/response validation.

These schemas define the contract between the FastAPI backend and frontend,
ensuring type safety and automatic OpenAPI documentation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DesignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    top_module: str = "top"
    description: str = ""
    config_path: str = ""
    work_root: str = ""
    pdk_name: str = ""
    target_utilization: float = 0.7
    clock_period_ns: float = 10.0


class DesignUpdate(BaseModel):
    description: str | None = None
    status: str | None = None
    target_utilization: float | None = None
    clock_period_ns: float | None = None


class DesignResponse(BaseModel):
    id: int
    name: str
    top_module: str
    description: str
    config_path: str
    work_root: str
    pdk_name: str
    target_utilization: float
    clock_period_ns: float
    status: str
    created_at: str | None
    updated_at: str | None
    stage_count: int = 0


class TimingData(BaseModel):
    wns: float | None = None
    tns: float | None = None
    violating_paths: int | None = None
    endpoints: int | None = None


class AreaData(BaseModel):
    total: float | None = None
    utilization: float | None = None
    std_cells: int | None = None


class PowerData(BaseModel):
    total_mw: float | None = None
    dynamic_mw: float | None = None
    leakage_mw: float | None = None


class RouteData(BaseModel):
    drc_errors: int | None = None
    wirelength: float | None = None


class StageResponse(BaseModel):
    id: int
    design_id: int
    stage_name: str
    tool: str
    flow_stage: str
    status: str
    work_dir: str
    log_file: str
    elapsed_seconds: float
    started_at: str | None
    finished_at: str | None
    timing: TimingData
    area: AreaData
    power: PowerData
    route: RouteData
    messages: list[str]
    output_files: dict[str, str]
    created_at: str | None


class StageRunRequest(BaseModel):
    design_id: int
    stage_name: str
    dry_run: bool = False


class MetricResponse(BaseModel):
    id: int
    design_id: int
    stage_id: int | None
    iteration: int
    snapshot_at: str | None
    wns: float | None
    tns: float | None
    utilization: float | None
    total_power_mw: float | None
    leakage_power_mw: float | None
    drc_errors: int | None
    num_violating_paths: int | None
    num_endpoints: int | None
    extra: dict[str, Any]


class MetricQuery(BaseModel):
    design_id: int | None = None
    limit: int = 50


class ScriptResponse(BaseModel):
    id: int
    design_id: int
    stage_name: str
    script_type: str
    filename: str
    content: str
    preview_content: str
    status: str
    exit_code: int | None
    execution_log: str
    generated_at: str | None
    executed_at: str | None


class ScriptRunRequest(BaseModel):
    script_id: int
    confirmed: bool = False


class GitCommitResponse(BaseModel):
    id: int
    design_id: int | None
    commit_hash: str
    short_hash: str
    author: str
    email: str
    message: str
    branch: str
    files_changed: int
    insertions: int
    deletions: int
    changed_files: list[str]
    committed_at: str | None
    recorded_at: str | None


class GitDiffRequest(BaseModel):
    commit_a: str
    commit_b: str = "HEAD"
    file_path: str = ""


class GitActionRequest(BaseModel):
    repo_path: str
    action: str  # commit, pull, push, status, log, diff
    message: str = ""
    files: list[str] = []


class FlowStatusResponse(BaseModel):
    design_name: str
    total_stages: int
    completed: list[str]
    failed: list[str]
    skipped: list[str]
    stage_times: dict[str, float]
    has_fatal_errors: bool


class DashboardSummary(BaseModel):
    total_designs: int
    active_designs: int
    total_stages_run: int
    passing_stages: int
    failing_stages: int
    recent_activity: list[dict[str, Any]]
