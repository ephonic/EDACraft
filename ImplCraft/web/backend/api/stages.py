"""
Stages API — flow stage management and execution.

Endpoints:
- GET    /api/stages/{design_id}       — List stages for a design
- POST   /api/stages/run               — Run a stage
- GET    /api/stages/detail/{stage_id} — Get stage details
- GET    /api/stages/{design_id}/log/{stage_name} — Get stage log content
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import desc

from ..db.engine import get_session
from ..db.models import DesignRecord, StageRecord
from ..db.schemas import StageResponse, StageRunRequest
from ..services.script_executor import ScriptExecutor

router = APIRouter()

# Global executor instance
_executor = ScriptExecutor()


@router.get("/stages/{design_id}", response_model=list[StageResponse])
def list_stages(design_id: int):
    """List all stages for a design."""
    with get_session() as session:
        stages = (
            session.query(StageRecord)
            .filter_by(design_id=design_id)
            .order_by(desc(StageRecord.created_at))
            .all()
        )
        return [s.to_dict() for s in stages]


@router.post("/stages/run")
def run_stage(request: StageRunRequest, background_tasks: BackgroundTasks):
    """
    Run a flow stage for a design.
    
    In dry_run mode, generates scripts without executing tools.
    In normal mode, launches the EDA tool in background.
    """
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=request.design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail=f"Design {request.design_id} not found")

        # Create stage record
        stage = StageRecord(
            design_id=request.design_id,
            stage_name=request.stage_name,
            status="pending",
        )
        session.add(stage)
        session.flush()
        stage_id = stage.id

    if request.dry_run:
        return {
            "stage_id": stage_id,
            "status": "dry_run",
            "message": f"Stage '{request.stage_name}' prepared (dry run)",
        }

    # Update status to running
    with get_session() as session:
        stage = session.query(StageRecord).filter_by(id=stage_id).first()
        stage.status = "running"
        stage.started_at = datetime.now(timezone.utc)

    # TODO: Integrate with actual flow orchestrator
    # For now, mark as completed with placeholder
    with get_session() as session:
        stage = session.query(StageRecord).filter_by(id=stage_id).first()
        stage.status = "completed"
        stage.finished_at = datetime.now(timezone.utc)
        stage.messages = [f"Stage {request.stage_name} completed (placeholder)"]

    return {
        "stage_id": stage_id,
        "status": "completed",
        "message": f"Stage '{request.stage_name}' completed",
    }


@router.get("/stages/detail/{stage_id}", response_model=StageResponse)
def get_stage_detail(stage_id: int):
    """Get detailed stage information."""
    with get_session() as session:
        stage = session.query(StageRecord).filter_by(id=stage_id).first()
        if not stage:
            raise HTTPException(status_code=404, detail=f"Stage {stage_id} not found")
        return stage.to_dict()


@router.get("/stages/{design_id}/log/{stage_name}")
def get_stage_log(design_id: int, stage_name: str):
    """Get the log file content for a stage."""
    with get_session() as session:
        stage = (
            session.query(StageRecord)
            .filter_by(design_id=design_id, stage_name=stage_name)
            .order_by(desc(StageRecord.created_at))
            .first()
        )
        if not stage:
            raise HTTPException(status_code=404, detail="Stage not found")

        log_path = Path(stage.log_file)
        if not log_path.exists():
            return {"log_file": stage.log_file, "content": "", "error": "Log file not found"}

        content = log_path.read_text(errors="replace")
        return {
            "log_file": str(log_path),
            "content": content,
            "size": len(content),
            "lines": content.count("\n"),
        }


@router.get("/stages/{design_id}/flow-status")
def get_flow_status(design_id: int):
    """Get overall flow status for a design."""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

        stages = (
            session.query(StageRecord)
            .filter_by(design_id=design_id)
            .order_by(StageRecord.id)
            .all()
        )

        stage_names = [
            "synthesis", "create_lib", "floorplan", "placement",
            "cts", "routing", "route_opt", "primetime", "drc", "lvs",
        ]

        completed = []
        failed = []
        pending = []
        running = []

        for sn in stage_names:
            matching = [s for s in stages if s.stage_name == sn]
            if matching:
                latest = matching[-1]
                if latest.status == "completed" or latest.status == "passed":
                    completed.append(sn)
                elif latest.status == "failed":
                    failed.append(sn)
                elif latest.status == "running":
                    running.append(sn)
                else:
                    pending.append(sn)
            else:
                pending.append(sn)

        return {
            "design_name": design.name,
            "total_stages": len(stage_names),
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "running": running,
            "stage_details": [s.to_dict() for s in stages],
        }
