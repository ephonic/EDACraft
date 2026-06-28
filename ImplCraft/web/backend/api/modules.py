"""
Modules API — partitioned module management and per-module execution tracking.

Endpoints:
- GET    /api/modules/{design_id}           — List all modules for a design
- POST   /api/modules/{design_id}           — Add a module
- POST   /api/modules/{design_id}/partition  — Auto-partition: add multiple modules
- PUT    /api/modules/{module_id}           — Update module info
- DELETE /api/modules/{module_id}           — Delete a module
- POST   /api/modules/{module_id}/stage/{stage_name}/start  — Mark stage started
- POST   /api/modules/{module_id}/stage/{stage_name}/complete — Mark stage completed
- POST   /api/modules/{module_id}/stage/{stage_name}/fail    — Mark stage failed
- GET    /api/modules/{design_id}/progress  — Get module progress matrix
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..db.engine import get_session
from ..db.models import ModuleRecord, DesignRecord

router = APIRouter()


class ModuleCreate(BaseModel):
    name: str
    hierarchy: str = ""
    parent_name: str | None = None
    level: int = 0
    area_um: float | None = None
    cell_count: int | None = None


class PartitionRequest(BaseModel):
    modules: list[ModuleCreate]


class ModuleUpdate(BaseModel):
    name: str | None = None
    hierarchy: str | None = None
    area_um: float | None = None
    cell_count: int | None = None


class StageCompleteRequest(BaseModel):
    elapsed: float = 0.0


@router.get("/modules/{design_id}")
def list_modules(design_id: int):
    """List all modules for a design."""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

        modules = session.query(ModuleRecord).filter_by(design_id=design_id).order_by(ModuleRecord.level, ModuleRecord.name).all()
        return [m.to_dict() for m in modules]


@router.post("/modules/{design_id}", status_code=201)
def add_module(design_id: int, data: ModuleCreate):
    """Add a single module to a design."""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

        existing = session.query(ModuleRecord).filter_by(design_id=design_id, name=data.name).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Module '{data.name}' already exists")

        record = ModuleRecord(
            design_id=design_id,
            name=data.name,
            hierarchy=data.hierarchy or data.name,
            parent_name=data.parent_name,
            level=data.level,
            area_um=data.area_um,
            cell_count=data.cell_count,
        )
        session.add(record)
        session.flush()
        return record.to_dict()


@router.post("/modules/{design_id}/partition", status_code=201)
def partition_design(design_id: int, data: PartitionRequest):
    """Add multiple modules at once (partition a design)."""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

        # Remove old modules and add new ones
        session.query(ModuleRecord).filter_by(design_id=design_id).delete()

        created = []
        for m in data.modules:
            record = ModuleRecord(
                design_id=design_id,
                name=m.name,
                hierarchy=m.hierarchy or m.name,
                parent_name=m.parent_name,
                level=m.level,
                area_um=m.area_um,
                cell_count=m.cell_count,
            )
            session.add(record)
            session.flush()
            created.append(record.to_dict())

        return {"modules": created, "count": len(created)}


@router.put("/modules/{module_id}")
def update_module(module_id: int, data: ModuleUpdate):
    """Update module info."""
    with get_session() as session:
        record = session.query(ModuleRecord).filter_by(id=module_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Module {module_id} not found")

        if data.name is not None:
            record.name = data.name
        if data.hierarchy is not None:
            record.hierarchy = data.hierarchy
        if data.area_um is not None:
            record.area_um = data.area_um
        if data.cell_count is not None:
            record.cell_count = data.cell_count

        record.updated_at = datetime.now(timezone.utc)
        return record.to_dict()


@router.delete("/modules/{module_id}", status_code=204)
def delete_module(module_id: int):
    """Delete a module."""
    with get_session() as session:
        record = session.query(ModuleRecord).filter_by(id=module_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
        session.delete(record)


def _update_stage_status(module_id: int, stage_name: str, status: str, elapsed: float = 0.0):
    """Helper to update a module's stage status."""
    valid_stages = ModuleRecord.STAGE_NAMES
    if stage_name not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage '{stage_name}'. Valid: {valid_stages}")

    with get_session() as session:
        record = session.query(ModuleRecord).filter_by(id=module_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Module {module_id} not found")

        record.set_stage_status(stage_name, status)
        if status == "completed" and elapsed > 0:
            record.set_stage_elapsed(stage_name, elapsed)

        # Update design status based on module progress
        _sync_design_status(session, record.design_id)

        record.updated_at = datetime.now(timezone.utc)
        return record.to_dict()


def _sync_design_status(session, design_id: int):
    """Sync parent design status based on all module progress."""
    modules = session.query(ModuleRecord).filter_by(design_id=design_id).all()
    if not modules:
        return

    design = session.query(DesignRecord).filter_by(id=design_id).first()
    if not design:
        return

    # If any module has a running stage, design is running
    for m in modules:
        for sn in ModuleRecord.STAGE_NAMES:
            if m.get_stage_status(sn) == "running":
                design.status = "running"
                return

    # If all modules completed all stages, design is completed
    all_completed = all(
        all(m.get_stage_status(sn) in ("completed", "skipped") for sn in ModuleRecord.STAGE_NAMES)
        for m in modules
    )
    if all_completed:
        design.status = "completed"
        return

    # If any module has a failed stage, design is partially_failed
    any_failed = any(
        any(m.get_stage_status(sn) == "failed" for sn in ModuleRecord.STAGE_NAMES)
        for m in modules
    )
    if any_failed:
        design.status = "partially_failed"


@router.post("/modules/{module_id}/stage/{stage_name}/start")
def start_module_stage(module_id: int, stage_name: str):
    """Mark a module's stage as started."""
    return _update_stage_status(module_id, stage_name, "running")


@router.post("/modules/{module_id}/stage/{stage_name}/complete")
def complete_module_stage(module_id: int, stage_name: str, data: StageCompleteRequest = StageCompleteRequest()):
    """Mark a module's stage as completed."""
    return _update_stage_status(module_id, stage_name, "completed", data.elapsed)


@router.post("/modules/{module_id}/stage/{stage_name}/fail")
def fail_module_stage(module_id: int, stage_name: str):
    """Mark a module's stage as failed."""
    return _update_stage_status(module_id, stage_name, "failed")


@router.get("/modules/{design_id}/progress")
def get_module_progress(design_id: int):
    """Get a progress matrix: modules x stages with status."""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

        modules = session.query(ModuleRecord).filter_by(design_id=design_id).order_by(ModuleRecord.level, ModuleRecord.name).all()

        if not modules:
            return {
                "design_id": design_id,
                "design_name": design.name,
                "stage_names": ModuleRecord.STAGE_NAMES,
                "modules": [],
                "summary": {"total": 0, "completed": 0, "running": 0, "failed": 0, "pending": 0},
            }

        module_data = []
        summary = {"total": len(modules), "completed": 0, "running": 0, "failed": 0, "pending": 0}

        for m in modules:
            md = m.to_dict()
            # Determine overall module status
            statuses = [m.get_stage_status(sn) for sn in ModuleRecord.STAGE_NAMES]
            if "running" in statuses:
                md["overall_status"] = "running"
                summary["running"] += 1
            elif "failed" in statuses:
                md["overall_status"] = "failed"
                summary["failed"] += 1
            elif all(s in ("completed", "skipped") for s in statuses):
                md["overall_status"] = "completed"
                summary["completed"] += 1
            else:
                md["overall_status"] = "pending"
                summary["pending"] += 1

            # Count completed stages for progress bar
            completed_count = sum(1 for s in statuses if s in ("completed", "skipped"))
            md["progress_pct"] = int(completed_count / len(ModuleRecord.STAGE_NAMES) * 100)
            module_data.append(md)

        return {
            "design_id": design_id,
            "design_name": design.name,
            "stage_names": ModuleRecord.STAGE_NAMES,
            "modules": module_data,
            "summary": summary,
        }
