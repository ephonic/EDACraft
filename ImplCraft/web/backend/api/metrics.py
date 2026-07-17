"""
Metrics API — QoR metrics and trend data.

Endpoints:
- GET    /api/metrics/{design_id}     — Get metrics history
- POST   /api/metrics/{design_id}     — Record new metrics snapshot
- GET    /api/metrics/{design_id}/trends — Get trend data for charts
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc

from ..db.engine import get_session
from ..db.models import DesignRecord, MetricRecord
from ..db.schemas import MetricResponse

router = APIRouter()


class MetricCreate(BaseModel):
    stage_id: int | None = None
    iteration: int = 1
    wns: float | None = None
    tns: float | None = None
    utilization: float | None = None
    total_power_mw: float | None = None
    leakage_power_mw: float | None = None
    drc_errors: int | None = None
    num_violating_paths: int | None = None
    num_endpoints: int | None = None
    extra: dict = {}


@router.get("/metrics/{design_id}", response_model=list[MetricResponse])
def list_metrics(
    design_id: int,
    limit: int = Query(default=50, le=200),
):
    """Get metrics history for a design."""
    with get_session() as session:
        metrics = (
            session.query(MetricRecord)
            .filter_by(design_id=design_id)
            .order_by(desc(MetricRecord.iteration))
            .limit(limit)
            .all()
        )
        return [m.to_dict() for m in metrics]


@router.post("/metrics/{design_id}", response_model=MetricResponse, status_code=201)
def create_metric(design_id: int, data: MetricCreate):
    """Record a new metrics snapshot."""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

        record = MetricRecord(
            design_id=design_id,
            stage_id=data.stage_id,
            iteration=data.iteration,
            wns=data.wns,
            tns=data.tns,
            utilization=data.utilization,
            total_power_mw=data.total_power_mw,
            leakage_power_mw=data.leakage_power_mw,
            drc_errors=data.drc_errors,
            num_violating_paths=data.num_violating_paths,
            num_endpoints=data.num_endpoints,
            extra=data.extra,
        )
        session.add(record)
        session.flush()
        return record.to_dict()


@router.get("/metrics/{design_id}/trends")
def get_metric_trends(design_id: int):
    """
    Get trend data formatted for charting.
    Returns time-series arrays for each metric.
    """
    with get_session() as session:
        metrics = (
            session.query(MetricRecord)
            .filter_by(design_id=design_id)
            .order_by(MetricRecord.iteration)
            .all()
        )

        trends = {
            "iterations": [],
            "timestamps": [],
            "wns": [],
            "tns": [],
            "utilization": [],
            "total_power_mw": [],
            "leakage_power_mw": [],
            "drc_errors": [],
            "num_violating_paths": [],
        }

        for m in metrics:
            trends["iterations"].append(m.iteration)
            trends["timestamps"].append(
                m.snapshot_at.isoformat() if m.snapshot_at else ""
            )
            trends["wns"].append(m.wns)
            trends["tns"].append(m.tns)
            trends["utilization"].append(m.utilization)
            trends["total_power_mw"].append(m.total_power_mw)
            trends["leakage_power_mw"].append(m.leakage_power_mw)
            trends["drc_errors"].append(m.drc_errors)
            trends["num_violating_paths"].append(m.num_violating_paths)

        return trends
