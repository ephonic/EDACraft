"""
Designs API — CRUD operations for design projects.

Endpoints:
- GET    /api/designs          — List all designs
- POST   /api/designs          — Create a new design
- GET    /api/designs/{id}     — Get design details
- PUT    /api/designs/{id}     — Update design
- DELETE /api/designs/{id}     — Delete design
- GET    /api/designs/{id}/config — Get design YAML config
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc

from ..db.engine import get_session
from ..db.models import DesignRecord, StageRecord
from ..db.schemas import DesignCreate, DesignUpdate, DesignResponse

router = APIRouter()


@router.get("/designs", response_model=list[DesignResponse])
def list_designs(
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List all design projects."""
    with get_session() as session:
        query = session.query(DesignRecord)
        if status:
            query = query.filter_by(status=status)
        designs = query.order_by(desc(DesignRecord.updated_at)).offset(offset).limit(limit).all()
        return [d.to_dict() for d in designs]


@router.post("/designs", response_model=DesignResponse, status_code=201)
def create_design(data: DesignCreate):
    """Create a new design project."""
    with get_session() as session:
        existing = session.query(DesignRecord).filter_by(name=data.name).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Design '{data.name}' already exists")

        record = DesignRecord(
            name=data.name,
            top_module=data.top_module,
            description=data.description,
            config_path=data.config_path,
            work_root=data.work_root,
            pdk_name=data.pdk_name,
            target_utilization=data.target_utilization,
            clock_period_ns=data.clock_period_ns,
            status="created",
        )
        session.add(record)
        session.flush()
        return record.to_dict()


@router.get("/designs/{design_id}", response_model=DesignResponse)
def get_design(design_id: int):
    """Get design details."""
    with get_session() as session:
        record = session.query(DesignRecord).filter_by(id=design_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")
        return record.to_dict()


@router.put("/designs/{design_id}", response_model=DesignResponse)
def update_design(design_id: int, data: DesignUpdate):
    """Update design properties."""
    with get_session() as session:
        record = session.query(DesignRecord).filter_by(id=design_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

        if data.description is not None:
            record.description = data.description
        if data.status is not None:
            record.status = data.status
        if data.target_utilization is not None:
            record.target_utilization = data.target_utilization
        if data.clock_period_ns is not None:
            record.clock_period_ns = data.clock_period_ns

        record.updated_at = datetime.now(timezone.utc)
        return record.to_dict()


@router.delete("/designs/{design_id}", status_code=204)
def delete_design(design_id: int):
    """Delete a design and all associated records."""
    with get_session() as session:
        record = session.query(DesignRecord).filter_by(id=design_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")
        session.delete(record)


@router.get("/designs/{design_id}/config")
def get_design_config(design_id: int):
    """Get the YAML configuration content for a design."""
    from pathlib import Path

    with get_session() as session:
        record = session.query(DesignRecord).filter_by(id=design_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

        config_path = Path(record.config_path)
        if not config_path.exists():
            return {"config_path": record.config_path, "content": "", "error": "File not found"}

        content = config_path.read_text(errors="replace")
        return {
            "config_path": str(config_path),
            "content": content,
            "size": len(content),
        }
