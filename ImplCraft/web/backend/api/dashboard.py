"""
Dashboard API — aggregated overview and summary data.

Endpoints:
- GET /api/dashboard/summary    — High-level dashboard metrics
- GET /api/dashboard/activity   — Recent activity feed
- GET /api/dashboard/designs-overview — All designs with status summary
"""
from __future__ import annotations

from sqlalchemy import func, desc

from fastapi import APIRouter, Query

from ..db.engine import get_session
from ..db.models import DesignRecord, StageRecord, MetricRecord, ScriptRecord

router = APIRouter()


@router.get("/dashboard/summary")
def get_summary():
    """Get high-level dashboard summary metrics."""
    with get_session() as session:
        total_designs = session.query(func.count(DesignRecord.id)).scalar() or 0
        active_designs = (
            session.query(func.count(DesignRecord.id))
            .filter(DesignRecord.status.in_(["created", "running", "in_progress"]))
            .scalar() or 0
        )
        total_stages = session.query(func.count(StageRecord.id)).scalar() or 0
        passing_stages = (
            session.query(func.count(StageRecord.id))
            .filter(StageRecord.status.in_(["completed", "passed"]))
            .scalar() or 0
        )
        failing_stages = (
            session.query(func.count(StageRecord.id))
            .filter_by(status="failed")
            .scalar() or 0
        )
        total_scripts = session.query(func.count(ScriptRecord.id)).scalar() or 0

        return {
            "total_designs": total_designs,
            "active_designs": active_designs,
            "total_stages_run": total_stages,
            "passing_stages": passing_stages,
            "failing_stages": failing_stages,
            "total_scripts": total_scripts,
        }


@router.get("/dashboard/activity")
def get_activity(limit: int = Query(default=20, le=50)):
    """Get recent activity feed across all entities."""
    with get_session() as session:
        activities = []

        recent_stages = (
            session.query(StageRecord)
            .order_by(desc(StageRecord.created_at))
            .limit(limit)
            .all()
        )
        for s in recent_stages:
            design = session.query(DesignRecord).filter_by(id=s.design_id).first()
            activities.append({
                "type": "stage",
                "timestamp": s.created_at.isoformat() if s.created_at else "",
                "design_name": design.name if design else "unknown",
                "stage_name": s.stage_name,
                "status": s.status,
                "message": f"Stage '{s.stage_name}' {s.status}",
            })

        recent_scripts = (
            session.query(ScriptRecord)
            .order_by(desc(ScriptRecord.generated_at))
            .limit(limit)
            .all()
        )
        for sc in recent_scripts:
            design = session.query(DesignRecord).filter_by(id=sc.design_id).first()
            activities.append({
                "type": "script",
                "timestamp": sc.generated_at.isoformat() if sc.generated_at else "",
                "design_name": design.name if design else "unknown",
                "filename": sc.filename,
                "status": sc.status,
                "message": f"Script '{sc.filename}' {sc.status}",
            })

        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]


@router.get("/dashboard/designs-overview")
def get_designs_overview():
    """Get all designs with their latest status and metrics."""
    with get_session() as session:
        designs = session.query(DesignRecord).order_by(desc(DesignRecord.updated_at)).all()
        overview = []

        for design in designs:
            stages = (
                session.query(StageRecord)
                .filter_by(design_id=design.id)
                .order_by(StageRecord.id)
                .all()
            )

            latest_metrics = (
                session.query(MetricRecord)
                .filter_by(design_id=design.id)
                .order_by(desc(MetricRecord.iteration))
                .first()
            )

            stage_summary = {}
            for s in stages:
                if s.stage_name not in stage_summary:
                    stage_summary[s.stage_name] = s.status

            overview.append({
                "id": design.id,
                "name": design.name,
                "status": design.status,
                "pdk": design.pdk_name,
                "clock_period_ns": design.clock_period_ns,
                "stages": stage_summary,
                "latest_metrics": {
                    "wns": latest_metrics.wns,
                    "tns": latest_metrics.tns,
                    "utilization": latest_metrics.utilization,
                    "drc_errors": latest_metrics.drc_errors,
                } if latest_metrics else None,
                "updated_at": design.updated_at.isoformat() if design.updated_at else None,
            })

        return overview
