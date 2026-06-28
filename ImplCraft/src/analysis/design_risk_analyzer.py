"""
Design Risk Analyzer — identifies uncertainties and risks across the backend flow.

Provides:
- Pre-flight validation before each EDA stage
- Risk scoring with confidence levels
- Actionable recommendations with decision points
- Cross-stage dependency risk propagation
- Early warning for common failure modes (PG, DRC, timing, LVS)
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ..db.design_state import DesignState, FlowStage, StageStatus

logger = logging.getLogger("ic_backend")


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    PG_CONNECTIVITY = "pg_connectivity"
    TIMING = "timing"
    DRC = "drc"
    LVS = "lvs"
    CONGESTION = "congestion"
    CTS = "cts"
    POWER = "power"
    UTILIZATION = "utilization"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"


@dataclass
class RiskItem:
    """A single identified risk with confidence and recommendation."""
    category: RiskCategory
    level: RiskLevel
    title: str
    description: str
    confidence: float  # 0.0 - 1.0, how confident we are about this risk
    affected_stage: str
    recommendation: str
    decision_required: bool = False
    decision_options: list[dict[str, str]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "affected_stage": self.affected_stage,
            "recommendation": self.recommendation,
            "decision_required": self.decision_required,
            "decision_options": self.decision_options,
            "metrics": self.metrics,
        }


@dataclass
class StageRiskReport:
    """Risk assessment for a specific flow stage."""
    stage_name: str
    overall_risk: RiskLevel
    confidence: float
    risks: list[RiskItem] = field(default_factory=list)
    pre_flight_pass: bool = True
    blocking_risks: list[RiskItem] = field(default_factory=list)
    warnings: list[RiskItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage_name": self.stage_name,
            "overall_risk": self.overall_risk.value,
            "confidence": self.confidence,
            "pre_flight_pass": self.pre_flight_pass,
            "risks": [r.to_dict() for r in self.risks],
            "blocking_risks": [r.to_dict() for r in self.blocking_risks],
            "warnings": [r.to_dict() for r in self.warnings],
        }


@dataclass
class DesignRiskReport:
    """Comprehensive risk report for the entire design."""
    design_name: str
    overall_risk: RiskLevel
    overall_confidence: float
    stage_reports: dict[str, StageRiskReport] = field(default_factory=dict)
    cross_stage_risks: list[RiskItem] = field(default_factory=list)
    decisions_pending: list[RiskItem] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "design_name": self.design_name,
            "overall_risk": self.overall_risk.value,
            "overall_confidence": self.overall_confidence,
            "stage_reports": {k: v.to_dict() for k, v in self.stage_reports.items()},
            "cross_stage_risks": [r.to_dict() for r in self.cross_stage_risks],
            "decisions_pending": [r.to_dict() for r in self.decisions_pending],
            "summary": self.summary,
        }


class DesignRiskAnalyzer:
    """
    Analyzes design state to identify risks, uncertainties, and decision points.

    Usage:
        analyzer = DesignRiskAnalyzer(design_state)
        report = analyzer.analyze_all()
        # or for pre-flight:
        preflight = analyzer.pre_flight_check("routing")
    """

    def __init__(self, state: DesignState, work_root: str | Path = ""):
        self.state = state
        self.work_root = Path(work_root) if work_root else Path(state.work_root)

    # -------------------------------------------------------------------------
    # Main entry points
    # -------------------------------------------------------------------------
    def analyze_all(self) -> DesignRiskReport:
        """Analyze risks across all flow stages."""
        stage_names = [
            "synthesis", "create_lib", "floorplan", "placement",
            "cts", "routing", "route_opt", "finish", "drc", "lvs",
        ]
        stage_reports: dict[str, StageRiskReport] = {}
        all_risks: list[RiskItem] = []

        for sn in stage_names:
            report = self._analyze_stage(sn)
            stage_reports[sn] = report
            all_risks.extend(report.risks)

        cross_stage = self._analyze_cross_stage_risks()
        all_risks.extend(cross_stage)

        decisions = [r for r in all_risks if r.decision_required]
        overall_risk = self._compute_overall_risk(all_risks)
        overall_conf = self._compute_overall_confidence(all_risks)
        summary = self._generate_summary(overall_risk, all_risks, decisions)

        return DesignRiskReport(
            design_name=self.state.config.design_name,
            overall_risk=overall_risk,
            overall_confidence=overall_conf,
            stage_reports=stage_reports,
            cross_stage_risks=cross_stage,
            decisions_pending=decisions,
            summary=summary,
        )

    def pre_flight_check(self, target_stage: str) -> StageRiskReport:
        """
        Pre-flight validation before running a specific stage.
        Returns a report indicating whether it's safe to proceed.
        """
        report = self._analyze_stage(target_stage)
        report.blocking_risks = [
            r for r in report.risks if r.level in (RiskLevel.CRITICAL, RiskLevel.HIGH)
        ]
        report.warnings = [
            r for r in report.risks if r.level == RiskLevel.MEDIUM
        ]
        report.pre_flight_pass = len(report.blocking_risks) == 0
        return report

    # -------------------------------------------------------------------------
    # Stage-specific analyzers
    # -------------------------------------------------------------------------
    def _analyze_stage(self, stage_name: str) -> StageRiskReport:
        """Dispatch to stage-specific risk analysis."""
        analyzers = {
            "synthesis": self._analyze_synthesis,
            "create_lib": self._analyze_create_lib,
            "floorplan": self._analyze_floorplan,
            "placement": self._analyze_placement,
            "cts": self._analyze_cts,
            "routing": self._analyze_routing,
            "route_opt": self._analyze_route_opt,
            "finish": self._analyze_finish,
            "drc": self._analyze_drc,
            "lvs": self._analyze_lvs,
        }
        analyzer_fn = analyzers.get(stage_name)
        if analyzer_fn:
            return analyzer_fn()
        return StageRiskReport(
            stage_name=stage_name,
            overall_risk=RiskLevel.LOW,
            confidence=0.5,
        )

    def _analyze_synthesis(self) -> StageRiskReport:
        risks: list[RiskItem] = []
        config = self.state.config

        # Check RTL files exist
        rtl_dir = Path(config.rtl_dir) if config.rtl_dir else None
        if rtl_dir and not rtl_dir.exists():
            risks.append(RiskItem(
                category=RiskCategory.CONFIGURATION,
                level=RiskLevel.CRITICAL,
                title="RTL directory not found",
                description=f"RTL directory does not exist: {rtl_dir}",
                confidence=1.0,
                affected_stage="synthesis",
                recommendation="Verify RTL directory path in config",
                decision_required=True,
                decision_options=[
                    {"label": "Fix RTL path", "action": "update_config"},
                    {"label": "Skip synthesis", "action": "skip_stage"},
                ],
            ))

        # Check clock period reasonableness
        if config.clock_period_ns < 1.0:
            risks.append(RiskItem(
                category=RiskCategory.TIMING,
                level=RiskLevel.HIGH,
                title="Very aggressive clock period",
                description=f"Clock period {config.clock_period_ns}ns may be difficult for this PDK",
                confidence=0.7,
                affected_stage="synthesis",
                recommendation="Consider relaxing clock or using pipeline stages",
                decision_required=True,
                decision_options=[
                    {"label": "Proceed anyway", "action": "continue"},
                    {"label": "Relax clock", "action": "update_clock"},
                ],
                metrics={"clock_period_ns": config.clock_period_ns},
            ))

        # Check synthesis result if available
        syn_result = self.state.stage_results.get(FlowStage.SYNTHESIS)
        if syn_result and syn_result.status == StageStatus.PASSED:
            if syn_result.timing.wns is not None and syn_result.timing.wns < 0:
                risks.append(RiskItem(
                    category=RiskCategory.TIMING,
                    level=RiskLevel.HIGH,
                    title="Setup violations after synthesis",
                    description=f"WNS = {syn_result.timing.wns:.3f}ns after synthesis",
                    confidence=0.9,
                    affected_stage="synthesis",
                    recommendation="Fix synthesis constraints or RTL before P&R",
                    decision_required=True,
                    decision_options=[
                        {"label": "Continue to P&R (ICC2 may fix)", "action": "continue"},
                        {"label": "Re-synthesize with relaxed constraints", "action": "resynthesize"},
                    ],
                    metrics={"wns": syn_result.timing.wns},
                ))

        return self._build_stage_report("synthesis", risks)

    def _analyze_create_lib(self) -> StageRiskReport:
        risks: list[RiskItem] = []
        pdk = self.state.config.pdk

        # Check tech file
        if pdk.tech_file and not Path(pdk.tech_file).exists():
            risks.append(RiskItem(
                category=RiskCategory.CONFIGURATION,
                level=RiskLevel.CRITICAL,
                title="Technology file not found",
                description=f"Missing tech file: {pdk.tech_file}",
                confidence=1.0,
                affected_stage="create_lib",
                recommendation="Verify PDK installation and tech file path",
                decision_required=True,
            ))

        # Check NDM libs
        for ndm in self.state.config.libraries.ndm_libs:
            if not Path(ndm).exists():
                risks.append(RiskItem(
                    category=RiskCategory.CONFIGURATION,
                    level=RiskLevel.CRITICAL,
                    title="NDM library not found",
                    description=f"Missing NDM library: {ndm}",
                    confidence=1.0,
                    affected_stage="create_lib",
                    recommendation="Generate NDM libraries or fix path",
                    decision_required=True,
                ))

        return self._build_stage_report("create_lib", risks)

    def _analyze_floorplan(self) -> StageRiskReport:
        risks: list[RiskItem] = []
        config = self.state.config

        # Check die size vs utilization
        die_area = config.die_width_um * config.die_height_um
        if die_area < 1000:
            risks.append(RiskItem(
                category=RiskCategory.UTILIZATION,
                level=RiskLevel.MEDIUM,
                title="Very small die area",
                description=f"Die area {die_area:.0f} um² may cause placement congestion",
                confidence=0.6,
                affected_stage="floorplan",
                recommendation="Consider increasing die size or reducing utilization target",
                metrics={"die_area_um2": die_area},
            ))

        return self._build_stage_report("floorplan", risks)

    def _analyze_placement(self) -> StageRiskReport:
        risks: list[RiskItem] = []
        config = self.state.config

        # Utilization check
        if config.target_utilization > 0.85:
            risks.append(RiskItem(
                category=RiskCategory.UTILIZATION,
                level=RiskLevel.HIGH,
                title="High utilization target",
                description=f"Target utilization {config.target_utilization:.0%} may cause congestion",
                confidence=0.8,
                affected_stage="placement",
                recommendation="Reduce utilization or increase die area",
                decision_required=True,
                decision_options=[
                    {"label": "Proceed with high utilization", "action": "continue"},
                    {"label": "Reduce to 0.7", "action": "reduce_utilization"},
                ],
            ))

        place_result = self.state.stage_results.get(FlowStage.PLACEMENT)
        if place_result and place_result.status == StageStatus.PASSED:
            if place_result.timing.wns is not None and place_result.timing.wns < -0.5:
                risks.append(RiskItem(
                    category=RiskCategory.TIMING,
                    level=RiskLevel.HIGH,
                    title="Large timing violations after placement",
                    description=f"WNS = {place_result.timing.wns:.3f}ns after placement",
                    confidence=0.85,
                    affected_stage="placement",
                    recommendation="Review placement congestion and timing-critical paths",
                ))
            if place_result.route.congestion_h is not None and place_result.route.congestion_h > 0.85:
                risks.append(RiskItem(
                    category=RiskCategory.CONGESTION,
                    level=RiskLevel.HIGH,
                    title="High horizontal congestion",
                    description=f"H-congestion = {place_result.route.congestion_h:.2f}",
                    confidence=0.9,
                    affected_stage="placement",
                    recommendation="Reduce utilization or adjust floorplan",
                ))

        return self._build_stage_report("placement", risks)

    def _analyze_cts(self) -> StageRiskReport:
        risks: list[RiskItem] = []
        config = self.state.config

        # CTS skew vs clock period ratio
        if config.clocks:
            clk = config.clocks[0]
            skew_ratio = clk.period_ns / config.cts.target_skew_ns if config.cts.target_skew_ns > 0 else 100
            if skew_ratio < 10:
                risks.append(RiskItem(
                    category=RiskCategory.CTS,
                    level=RiskLevel.MEDIUM,
                    title="Tight skew target relative to clock period",
                    description=f"Skew {config.cts.target_skew_ns}ns is {skew_ratio:.1f}x smaller than period",
                    confidence=0.7,
                    affected_stage="cts",
                    recommendation="Consider relaxing skew target if CTS fails to converge",
                ))

        # Check for redundant final_opto issue
        cts_dir = self.work_root / "cts"
        if cts_dir.exists():
            run_tcl = cts_dir / "run.tcl"
            if run_tcl.exists():
                tcl_content = run_tcl.read_text(errors="ignore")
                if tcl_content.count("final_opto") > 1:
                    risks.append(RiskItem(
                        category=RiskCategory.CTS,
                        level=RiskLevel.MEDIUM,
                        title="Redundant clock_opt final_opto in CTS script",
                        description="Multiple final_opto iterations detected; GRE mode may error",
                        confidence=0.95,
                        affected_stage="cts",
                        recommendation="Guard with conditional check or remove redundant iteration",
                    ))

        return self._build_stage_report("cts", risks)

    def _analyze_routing(self) -> StageRiskReport:
        risks: list[RiskItem] = []
        return self._build_stage_report("routing", risks)

    def _analyze_route_opt(self) -> StageRiskReport:
        risks: list[RiskItem] = []

        route_result = self.state.stage_results.get(FlowStage.ROUTE_OPT)
        if route_result and route_result.status == StageStatus.PASSED:
            if route_result.route.drc_errors is not None:
                if route_result.route.drc_errors > 0:
                    level = RiskLevel.HIGH if route_result.route.drc_errors > 50 else RiskLevel.MEDIUM
                    risks.append(RiskItem(
                        category=RiskCategory.DRC,
                        level=level,
                        title="Post-route DRC violations",
                        description=f"{route_result.route.drc_errors} DRC errors after route_opt",
                        confidence=0.95,
                        affected_stage="route_opt",
                        recommendation="Review DRC types; may need routing constraint relaxation or ECO fix",
                        decision_required=route_result.route.drc_errors > 10,
                        decision_options=[
                            {"label": "Proceed to sign-off (Calibre may differ)", "action": "continue"},
                            {"label": "Run ECO route repair", "action": "eco_repair"},
                        ],
                        metrics={"drc_errors": route_result.route.drc_errors},
                    ))

        # Check for open nets from log files
        route_opt_dir = self.work_root / "route_opt"
        if route_opt_dir.exists():
            for log_file in route_opt_dir.glob("*.log"):
                content = log_file.read_text(errors="ignore")
                open_match = re.search(r'(\d+)\s+open\s+net', content, re.IGNORECASE)
                if open_match:
                    open_count = int(open_match.group(1))
                    if open_count > 0:
                        risks.append(RiskItem(
                            category=RiskCategory.DRC,
                            level=RiskLevel.CRITICAL,
                            title="Open nets detected",
                            description=f"{open_count} open nets after route_opt",
                            confidence=0.9,
                            affected_stage="route_opt",
                            recommendation="Check routing congestion and fix before proceeding",
                            decision_required=True,
                        ))

        return self._build_stage_report("route_opt", risks)

    def _analyze_finish(self) -> StageRiskReport:
        risks: list[RiskItem] = []

        finish_dir = self.work_root / "finish" / "out"
        if finish_dir.exists():
            gds_file = finish_dir / "bp_pe.gds.gz"
            if not gds_file.exists():
                gds_files = list(finish_dir.glob("*.gds*"))
                if not gds_files:
                    risks.append(RiskItem(
                        category=RiskCategory.CONFIGURATION,
                        level=RiskLevel.HIGH,
                        title="No GDS output from finish stage",
                        description="GDS file not found in finish output directory",
                        confidence=1.0,
                        affected_stage="finish",
                        recommendation="Re-run finish stage or check write_gds settings",
                    ))

        return self._build_stage_report("finish", risks)

    def _analyze_drc(self) -> StageRiskReport:
        risks: list[RiskItem] = []

        drc_dir = self.work_root / "drc"
        if drc_dir.exists():
            for rpt in drc_dir.rglob("*.rpt"):
                content = rpt.read_text(errors="ignore")
                total_match = re.search(r'TOTAL\s+Results\s*=\s*(\d+)', content)
                if total_match:
                    total = int(total_match.group(1))
                    if total > 0:
                        risks.append(RiskItem(
                            category=RiskCategory.DRC,
                            level=RiskLevel.HIGH if total > 20 else RiskLevel.MEDIUM,
                            title="Calibre DRC violations",
                            description=f"{total} total DRC violations",
                            confidence=0.95,
                            affected_stage="drc",
                            recommendation="Review violation types; common fixes include spacing adjustment or metal fill",
                            metrics={"total_drc": total},
                        ))

        return self._build_stage_report("drc", risks)

    def _analyze_lvs(self) -> StageRiskReport:
        risks: list[RiskItem] = []
        config = self.state.config

        # Check LVS prerequisites
        pdk = config.pdk
        if pdk.std_cell_gds and not Path(pdk.std_cell_gds).exists():
            risks.append(RiskItem(
                category=RiskCategory.LVS,
                level=RiskLevel.CRITICAL,
                title="Standard cell GDS not found for LVS merge",
                description=f"Missing: {pdk.std_cell_gds}",
                confidence=1.0,
                affected_stage="lvs",
                recommendation="Verify std cell GDS path or generate from library",
                decision_required=True,
            ))

        if pdk.std_cell_spice and not Path(pdk.std_cell_spice).exists():
            risks.append(RiskItem(
                category=RiskCategory.LVS,
                level=RiskLevel.CRITICAL,
                title="Standard cell SPICE not found for LVS",
                description=f"Missing: {pdk.std_cell_spice}",
                confidence=1.0,
                affected_stage="lvs",
                recommendation="Verify std cell SPICE/CDL path",
                decision_required=True,
            ))

        # Check for PG connectivity issues from ICC2 logs
        pg_risk = self._check_pg_connectivity()
        if pg_risk:
            risks.append(pg_risk)

        return self._build_stage_report("lvs", risks)

    # -------------------------------------------------------------------------
    # PG connectivity analysis (common failure mode for small blocks)
    # -------------------------------------------------------------------------
    def _check_pg_connectivity(self) -> RiskItem | None:
        """Check for PG rail / std-cell power pin connectivity issues."""
        # Look for ICC2 check_pg_connectivity reports
        for log_name in ["icc2_output.txt", "check_pg.log"]:
            log_path = self.work_root / log_name
            if not log_path.exists():
                continue
            content = log_path.read_text(errors="ignore")

            # Pattern: "floating" or "unconnected" power/ground cells
            floating_match = re.search(r'(\d+)\s+(?:floating|unconnected)\s+(?:std|standard)\s*cell', content, re.IGNORECASE)
            if floating_match:
                count = int(floating_match.group(1))
                if count > 0:
                    return RiskItem(
                        category=RiskCategory.PG_CONNECTIVITY,
                        level=RiskLevel.HIGH if count > 10 else RiskLevel.MEDIUM,
                        title=f"{count} std cells with floating PG pins",
                        description=(
                            f"ICC2 reports {count} standard cells with unconnected power/ground. "
                            "This typically means M1 PG rails are not aligned to std-cell VDD/VSS contacts."
                        ),
                        confidence=0.85,
                        affected_stage="lvs",
                        recommendation=(
                            "Ensure create_pg_std_cell_conn_pattern uses -rail_width and -rail_shift "
                            "to align rails over std-cell contacts. Consider flattening the design."
                        ),
                        decision_required=True,
                        decision_options=[
                            {"label": "Proceed (Calibre may merge)", "action": "continue"},
                            {"label": "Fix PG rails first", "action": "fix_pg"},
                            {"label": "Flatten design", "action": "flatten"},
                        ],
                        metrics={"floating_pg_cells": count},
                    )
        return None

    # -------------------------------------------------------------------------
    # Cross-stage risk analysis
    # -------------------------------------------------------------------------
    def _analyze_cross_stage_risks(self) -> list[RiskItem]:
        """Identify risks that propagate across stages."""
        risks: list[RiskItem] = []

        # Check if synthesis has timing violations that will propagate
        syn_result = self.state.stage_results.get(FlowStage.SYNTHESIS)
        place_result = self.state.stage_results.get(FlowStage.PLACEMENT)
        if syn_result and place_result:
            if syn_result.timing.wns is not None and syn_result.timing.wns < 0:
                if place_result.timing.wns is not None and place_result.timing.wns < syn_result.timing.wns:
                    risks.append(RiskItem(
                        category=RiskCategory.TIMING,
                        level=RiskLevel.HIGH,
                        title="Timing degraded from synthesis to placement",
                        description=(
                            f"WNS worsened from {syn_result.timing.wns:.3f}ns (synth) to "
                            f"{place_result.timing.wns:.3f}ns (placement)"
                        ),
                        confidence=0.9,
                        affected_stage="placement",
                        recommendation="Review floorplan, congestion, and placement constraints",
                    ))

        # Check if design is too small for the PDK (PE-specific concern)
        config = self.state.config
        die_area = config.die_width_um * config.die_height_um
        if die_area < 5000 and config.target_utilization > 0.6:
            risks.append(RiskItem(
                category=RiskCategory.UTILIZATION,
                level=RiskLevel.MEDIUM,
                title="Small die with high utilization — PG rail risk",
                description=(
                    f"Die area {die_area:.0f} um² with {config.target_utilization:.0%} utilization. "
                    "Small blocks have limited space for PG mesh; M1 rails must be precisely aligned."
                ),
                confidence=0.75,
                affected_stage="placement",
                recommendation="Ensure pg_rail config has correct rail_width and rail_shift values",
            ))

        return risks

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _build_stage_report(self, stage_name: str, risks: list[RiskItem]) -> StageRiskReport:
        if not risks:
            return StageRiskReport(
                stage_name=stage_name,
                overall_risk=RiskLevel.LOW,
                confidence=0.9,
            )
        max_risk = max(risks, key=lambda r: _risk_priority(r.level))
        avg_conf = sum(r.confidence for r in risks) / len(risks)
        return StageRiskReport(
            stage_name=stage_name,
            overall_risk=max_risk.level,
            confidence=avg_conf,
            risks=risks,
            blocking_risks=[r for r in risks if r.level in (RiskLevel.CRITICAL, RiskLevel.HIGH)],
            warnings=[r for r in risks if r.level == RiskLevel.MEDIUM],
        )

    def _compute_overall_risk(self, risks: list[RiskItem]) -> RiskLevel:
        if not risks:
            return RiskLevel.LOW
        return max(risks, key=lambda r: _risk_priority(r.level)).level

    def _compute_overall_confidence(self, risks: list[RiskItem]) -> float:
        if not risks:
            return 0.9
        return min(r.confidence for r in risks)

    def _generate_summary(
        self, overall_risk: RiskLevel, risks: list[RiskItem], decisions: list[RiskItem]
    ) -> str:
        critical_count = sum(1 for r in risks if r.level == RiskLevel.CRITICAL)
        high_count = sum(1 for r in risks if r.level == RiskLevel.HIGH)
        parts = [f"Overall risk: {overall_risk.value.upper()}"]
        if critical_count:
            parts.append(f"{critical_count} critical issue(s)")
        if high_count:
            parts.append(f"{high_count} high-risk issue(s)")
        if decisions:
            parts.append(f"{len(decisions)} decision(s) pending")
        return " | ".join(parts)


def _risk_priority(level: RiskLevel) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(level.value, 0)
