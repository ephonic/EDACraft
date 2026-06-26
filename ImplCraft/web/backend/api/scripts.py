"""
Scripts API — script preview, confirmation, and execution workflow.

Endpoints:
- GET    /api/scripts/{design_id}        — List scripts for a design
- POST   /api/scripts/generate           — Generate a new script (preview)
- GET    /api/scripts/preview/{script_id} — Get script preview content
- POST   /api/scripts/execute            — Execute a confirmed script
- POST   /api/scripts/cancel/{script_id} — Cancel a running script
- GET    /api/scripts/log/{script_id}    — Get execution log
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import desc

from ..db.engine import get_session
from ..db.models import ScriptRecord, DesignRecord
from ..db.schemas import ScriptResponse, ScriptRunRequest
from ..services.script_executor import ScriptExecutor

router = APIRouter()

_executor = ScriptExecutor()


class ScriptGenerateRequest(BaseModel):
    design_id: int
    stage_name: str
    content: str
    filename: str = "run.tcl"
    script_type: str = "tcl"


@router.get("/scripts/{design_id}", response_model=list[ScriptResponse])
def list_scripts(
    design_id: int,
    status: str | None = None,
    limit: int = 50,
):
    """List scripts for a design."""
    with get_session() as session:
        query = session.query(ScriptRecord).filter_by(design_id=design_id)
        if status:
            query = query.filter_by(status=status)
        scripts = query.order_by(desc(ScriptRecord.generated_at)).limit(limit).all()
        return [s.to_dict() for s in scripts]


@router.post("/scripts/generate", response_model=ScriptResponse, status_code=201)
def generate_script(data: ScriptGenerateRequest):
    """Generate a new script and store for preview."""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=data.design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail=f"Design {data.design_id} not found")

    script_id = _executor.generate_script(
        design_id=data.design_id,
        stage_name=data.stage_name,
        content=data.content,
        filename=data.filename,
        script_type=data.script_type,
    )

    with get_session() as session:
        record = session.query(ScriptRecord).filter_by(id=script_id).first()
        return record.to_dict()


@router.get("/scripts/preview/{script_id}")
def preview_script(script_id: int):
    """Get script preview with annotations."""
    with get_session() as session:
        record = session.query(ScriptRecord).filter_by(id=script_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Script {script_id} not found")

        return {
            "id": record.id,
            "filename": record.filename,
            "script_type": record.script_type,
            "content": record.content,
            "preview_content": record.preview_content,
            "status": record.status,
            "line_count": len(record.content.split("\n")),
        }


@router.post("/scripts/execute")
def execute_script(request: ScriptRunRequest, background_tasks: BackgroundTasks):
    """
    Execute a script after user confirmation.
    
    The 'confirmed' flag must be True to actually execute.
    Dry run mode is available for testing without tool invocation.
    """
    with get_session() as session:
        record = session.query(ScriptRecord).filter_by(id=request.script_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Script {request.script_id} not found")

        if record.status == "running":
            raise HTTPException(status_code=409, detail="Script is already running")

    if not request.confirmed:
        return {
            "script_id": request.script_id,
            "status": "awaiting_confirmation",
            "message": "Set confirmed=true to execute the script",
        }

    result = _executor.execute_script(request.script_id)
    return result


@router.post("/scripts/cancel/{script_id}")
def cancel_script(script_id: int):
    """Cancel a running script."""
    cancelled = _executor.cancel_script(script_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Script not running or not found")
    return {"status": "cancelled", "script_id": script_id}


@router.get("/scripts/log/{script_id}")
def get_script_log(script_id: int):
    """Get execution log for a script."""
    with get_session() as session:
        record = session.query(ScriptRecord).filter_by(id=script_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Script {script_id} not found")

        return {
            "script_id": script_id,
            "filename": record.filename,
            "status": record.status,
            "exit_code": record.exit_code,
            "execution_log": record.execution_log,
            "executed_at": record.executed_at.isoformat() if record.executed_at else None,
        }


@router.get("/scripts/running")
def get_running_scripts():
    """Get list of currently running script IDs."""
    return {"running": _executor.get_running_scripts()}
