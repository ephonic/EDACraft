"""
Pre-flight Validator — validates design readiness before each EDA stage.

Integrates with FlowOrchestrator to provide:
- Automatic pre-flight checks before stage execution
- Risk-based go/no-go decisions
- User decision overrides for blocking risks
- Detailed validation reports
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..db.design_state import DesignState, FlowStage
from .design_risk_analyzer import (
    DesignRiskAnalyzer, RiskLevel, StageRiskReport, RiskItem,
)

logger = logging.getLogger("ic_backend")


@dataclass
class PreflightDecision:
    """A recorded user decision to override a blocking risk."""
    risk_title: str
    action: str
    reason: str = ""


@dataclass
class PreflightReport:
    """Result of pre-flight validation for a stage."""
    stage_name: str
    passed: bool
    risk_report: StageRiskReport
    effective_blocking: list[RiskItem] = field(default_factory=list)
    resolved_by_user: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "stage_name": self.stage_name,
            "passed": self.passed,
            "effective_blocking": [r.to_dict() for r in self.effective_blocking],
            "resolved_by_user": self.resolved_by_user,
            "recommendation": self.recommendation,
            "risk_report": self.risk_report.to_dict(),
        }


class PreflightValidator:
    """
    Validates design readiness before EDA stage execution.

    Usage:
        validator = PreflightValidator(design_state, work_root="./work")
        report = validator.validate("routing")
        if report.passed:
            # proceed with stage
        else:
            # show blocking risks to user
    """

    def __init__(self, state: DesignState, work_root: str | Path = ""):
        self.state = state
        self.work_root = Path(work_root) if work_root else Path(state.work_root)
        self.analyzer = DesignRiskAnalyzer(state, work_root=str(self.work_root))
        self._decisions: list[PreflightDecision] = []

    def validate(self, stage_name: str) -> PreflightReport:
        """Run pre-flight validation for a specific stage."""
        risk_report = self.analyzer.pre_flight_check(stage_name)

        # Filter out risks that have been resolved by user decisions
        decision_titles = {d.risk_title for d in self._decisions}
        effective_blocking = [
            r for r in risk_report.blocking_risks
            if r.title not in decision_titles
        ]
        resolved = [
            r.title for r in risk_report.blocking_risks
            if r.title in decision_titles
        ]

        passed = len(effective_blocking) == 0
        recommendation = self._generate_recommendation(stage_name, effective_blocking, passed)

        return PreflightReport(
            stage_name=stage_name,
            passed=passed,
            risk_report=risk_report,
            effective_blocking=effective_blocking,
            resolved_by_user=resolved,
            recommendation=recommendation,
        )

    def validate_all(self) -> dict[str, PreflightReport]:
        """Run pre-flight validation for all stages."""
        stages = [
            "synthesis", "create_lib", "floorplan", "placement",
            "cts", "routing", "route_opt", "finish", "drc", "lvs",
        ]
        return {sn: self.validate(sn) for sn in stages}

    def record_decision(self, risk_title: str, action: str, reason: str = ""):
        """Record a user decision to override a blocking risk."""
        self._decisions.append(PreflightDecision(
            risk_title=risk_title,
            action=action,
            reason=reason,
        ))
        logger.info(f"Decision recorded: '{risk_title}' -> {action}")

    def get_decisions(self) -> list[dict]:
        """Get all recorded decisions."""
        return [
            {"risk_title": d.risk_title, "action": d.action, "reason": d.reason}
            for d in self._decisions
        ]

    def _generate_recommendation(
        self, stage: str, blocking: list[RiskItem], passed: bool
    ) -> str:
        if passed:
            warnings = []
            for risk in self.analyzer.pre_flight_check(stage).warnings:
                warnings.append(risk.title)
            if warnings:
                return f"Proceed with caution: {len(warnings)} warning(s) — {'; '.join(warnings[:3])}"
            return "All checks passed — safe to proceed"

        critical = [r for r in blocking if r.level == RiskLevel.CRITICAL]
        if critical:
            return f"BLOCKED: {len(critical)} critical issue(s) must be resolved before {stage}"
        return f"BLOCKED: {len(blocking)} high-risk issue(s) — review and make decision to proceed"


class FlowPreflightIntegration:
    """
    Integrates pre-flight validation into the FlowOrchestrator.

    This is a mixin-style helper that can be used with the orchestrator:
        orchestrator = FlowOrchestrator(config, work_root="./work")
        integration = FlowPreflightIntegration(orchestrator)
        integration.enable_preflight()  # Enables pre-flight checks before each stage
    """

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator
        self.validator: PreflightValidator | None = None
        self.enabled = False
        self.auto_proceed_on_warning = True
        self.require_decision_on_block = True

    def enable_preflight(self):
        """Enable pre-flight validation before each stage."""
        self.validator = PreflightValidator(
            self.orchestrator.state,
            work_root=self.orchestrator.work_root,
        )
        self.enabled = True
        logger.info("Pre-flight validation enabled for flow orchestrator")

    def check_before_stage(self, stage_name: str) -> PreflightReport:
        """Check pre-flight before running a stage."""
        if not self.enabled or not self.validator:
            return PreflightReport(
                stage_name=stage_name,
                passed=True,
                risk_report=StageRiskReport(
                    stage_name=stage_name,
                    overall_risk=RiskLevel.LOW,
                    confidence=1.0,
                ),
                recommendation="Pre-flight disabled",
            )
        return self.validator.validate(stage_name)

    def record_decision(self, risk_title: str, action: str, reason: str = ""):
        """Record a user decision to proceed despite blocking risks."""
        if self.validator:
            self.validator.record_decision(risk_title, action, reason)
