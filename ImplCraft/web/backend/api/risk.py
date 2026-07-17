"""
Risk & Uncertainty API — pre-flight validation and risk visualization.

Endpoints:
- GET  /api/risk/analysis/{design_id}     — Full design risk analysis
- GET  /api/risk/preflight/{design_id}/{stage} — Pre-flight check for a stage
- POST /api/risk/decision/{design_id}      — Record a user decision
- GET  /api/risk/decisions/{design_id}     — List pending decisions
- GET  /api/risk/summary/{design_id}       — Risk summary for dashboard
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db.engine import get_session
from ..db.models import DesignRecord, StageRecord, MetricRecord

logger = logging.getLogger("implcraft.risk")

router = APIRouter()


class DecisionRecord(BaseModel):
    risk_id: str
    decision: str
    reason: str = ""
    timestamp: str = ""


# ---- In-memory decision store (could be persisted to DB) ----
_decisions: dict[int, list[dict]] = {}


def _get_design_state(design_id: int) -> dict | None:
    """Load design state JSON from work directory."""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if not design:
            return None

        # Try to find design_state.json in work directory
        work_root = design.work_dir or f"./work_{design.name}"
        state_file = Path(work_root) / "design_state.json"
        if state_file.exists():
            return json.loads(state_file.read_text())

        # Fallback: construct minimal state from DB
        stages = session.query(StageRecord).filter_by(design_id=design_id).all()
        metrics = (
            session.query(MetricRecord)
            .filter_by(design_id=design_id)
            .order_by(MetricRecord.iteration.desc())
            .first()
        )
        return {
            "design_name": design.name,
            "config": {
                "design_name": design.name,
                "top_module": design.top_module or "top",
                "clock_period_ns": design.clock_period_ns or 10.0,
                "pdk": {"name": design.pdk_name or "unknown"},
                "target_utilization": 0.7,
            },
            "stages": {s.stage_name: s.status for s in stages},
            "metrics": {
                "wns": metrics.wns if metrics else None,
                "tns": metrics.tns if metrics else None,
                "drc_errors": metrics.drc_errors if metrics else None,
                "utilization": metrics.utilization if metrics else None,
            },
        }


def _analyze_risks(state_data: dict, work_root: str = "") -> dict:
    """Run risk analysis on design state data."""
    from src.analysis.design_risk_analyzer import (
        DesignRiskAnalyzer, RiskLevel, DesignState,
    )

    try:
        ds = DesignState.from_dict(state_data)
        ds.work_root = work_root or ds.work_root
        analyzer = DesignRiskAnalyzer(ds, work_root=ds.work_root)
        report = analyzer.analyze_all()
        return report.to_dict()
    except Exception as e:
        logger.error(f"Risk analysis failed: {e}")
        return {
            "design_name": state_data.get("config", {}).get("design_name", "unknown"),
            "overall_risk": "unknown",
            "overall_confidence": 0.0,
            "stage_reports": {},
            "cross_stage_risks": [],
            "decisions_pending": [],
            "summary": f"Analysis failed: {e}",
        }


@router.get("/risk/analysis/{design_id}")
def get_risk_analysis(design_id: int):
    """Get comprehensive risk analysis for a design."""
    state_data = _get_design_state(design_id)
    if state_data is None:
        raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

    work_root = ""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if design and design.work_dir:
            work_root = design.work_dir

    return _analyze_risks(state_data, work_root)


@router.get("/risk/preflight/{design_id}/{stage}")
def get_preflight(design_id: int, stage: str):
    """Pre-flight validation before running a specific stage."""
    state_data = _get_design_state(design_id)
    if state_data is None:
        raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

    from src.analysis.design_risk_analyzer import DesignRiskAnalyzer, DesignState

    work_root = ""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if design and design.work_dir:
            work_root = design.work_dir

    try:
        ds = DesignState.from_dict(state_data)
        ds.work_root = work_root or ds.work_root
        analyzer = DesignRiskAnalyzer(ds, work_root=ds.work_root)
        report = analyzer.pre_flight_check(stage)

        # Check if user has made decisions for blocking risks
        user_decisions = _decisions.get(design_id, [])
        resolved_risks = []
        for risk in report.blocking_risks:
            for d in user_decisions:
                if d["risk_id"] == risk.title:
                    resolved_risks.append(risk)
                    break

        report_dict = report.to_dict()
        report_dict["resolved_by_user"] = len(resolved_risks)
        report_dict["effective_pass"] = (
            len(report.blocking_risks) - len(resolved_risks) == 0
        )
        return report_dict
    except Exception as e:
        logger.error(f"Pre-flight check failed: {e}")
        return {
            "stage_name": stage,
            "overall_risk": "unknown",
            "pre_flight_pass": False,
            "error": str(e),
        }


@router.post("/risk/decision/{design_id}")
def record_decision(design_id: int, decision: DecisionRecord):
    """Record a user decision on a risk item."""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

    if design_id not in _decisions:
        _decisions[design_id] = []

    _decisions[design_id].append({
        "risk_id": decision.risk_id,
        "decision": decision.decision,
        "reason": decision.reason,
        "timestamp": decision.timestamp or datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "recorded",
        "total_decisions": len(_decisions[design_id]),
    }


@router.get("/risk/decisions/{design_id}")
def list_decisions(design_id: int):
    """List all decisions made for a design."""
    return {
        "design_id": design_id,
        "decisions": _decisions.get(design_id, []),
    }


@router.get("/risk/summary/{design_id}")
def get_risk_summary(design_id: int):
    """Get a compact risk summary for the dashboard."""
    state_data = _get_design_state(design_id)
    if state_data is None:
        raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

    work_root = ""
    with get_session() as session:
        design = session.query(DesignRecord).filter_by(id=design_id).first()
        if design and design.work_dir:
            work_root = design.work_dir

    analysis = _analyze_risks(state_data, work_root)

    # Compact summary
    risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for stage_name, stage_report in analysis.get("stage_reports", {}).items():
        for risk in stage_report.get("risks", []):
            level = risk.get("level", "low")
            if level in risk_counts:
                risk_counts[level] += 1

    total_risks = sum(risk_counts.values())
    decisions_made = len(_decisions.get(design_id, []))
    decisions_pending = len(analysis.get("decisions_pending", []))

    return {
        "design_id": design_id,
        "overall_risk": analysis.get("overall_risk", "unknown"),
        "overall_confidence": analysis.get("overall_confidence", 0.0),
        "risk_counts": risk_counts,
        "total_risks": total_risks,
        "decisions_made": decisions_made,
        "decisions_pending": decisions_pending,
        "summary": analysis.get("summary", ""),
        "top_risks": [
            {
                "title": r["title"],
                "level": r["level"],
                "confidence": r["confidence"],
                "stage": r["affected_stage"],
            }
            for r in sorted(
                analysis.get("decisions_pending", []),
                key=lambda x: {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(x.get("level", "low"), 0),
                reverse=True,
            )[:5]
        ],
    }
