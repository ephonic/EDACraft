"""
QoR Analyzer — cross-stage Quality of Results analysis.

Compares metrics across stages, identifies regressions, and generates
actionable diagnostics for the agent layer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..db.design_state import DesignState, FlowStage, StageResult, StageStatus


@dataclass
class QoRDelta:
    """Delta between two stages for a single metric."""
    metric_name: str
    stage_before: str
    stage_after: str
    value_before: float | None
    value_after: float | None
    delta: float | None
    is_regression: bool = False
    comment: str = ""


@dataclass
class QoRDiagnosis:
    """Diagnosis result from QoR analysis."""
    design_name: str
    stage_results: dict[str, dict[str, Any]]
    deltas: list[QoRDelta]
    recommendations: list[str]
    summary: str = ""


class QoRAnalyzer:
    """
    Analyze Quality of Results across backend stages.

    Compares timing, area, power, and routing metrics between stages
    to identify regressions and suggest optimization strategies.
    """

    def __init__(self, state: DesignState):
        self.state = state

    def analyze(self) -> QoRDiagnosis:
        """Run full QoR analysis across all completed stages."""
        stage_metrics = {}
        deltas = []
        recommendations = []

        # Collect metrics from each stage
        ordered_stages = [
            FlowStage.SYNTHESIS,
            FlowStage.FLOORPLAN,
            FlowStage.PLACEMENT,
            FlowStage.CTS,
            FlowStage.ROUTING,
            FlowStage.ROUTE_OPT,
            FlowStage.PV_DRC,
            FlowStage.PV_LVS,
        ]

        prev_result = None
        prev_name = ""

        for stage in ordered_stages:
            result = self.state.stage_results.get(stage.name)
            if result is None or result.status == StageStatus.PENDING:
                continue

            stage_metrics[stage.name] = self._extract_metrics(result)

            if prev_result is not None:
                stage_deltas = self._compute_deltas(prev_name, prev_result, stage.name, result)
                deltas.extend(stage_deltas)

                # Check for regressions
                for d in stage_deltas:
                    if d.is_regression:
                        recommendations.extend(
                            self._recommend_fix(d, result)
                        )

            prev_result = result
            prev_name = stage.name

        summary = self._build_summary(stage_metrics, deltas)

        return QoRDiagnosis(
            design_name=self.state.config.design_name,
            stage_results=stage_metrics,
            deltas=deltas,
            recommendations=list(dict.fromkeys(recommendations)),  # dedupe
            summary=summary,
        )

    def _extract_metrics(self, result: StageResult) -> dict[str, Any]:
        """Extract key metrics from a stage result."""
        metrics: dict[str, Any] = {}

        if result.timing.wns is not None:
            metrics["wns_ns"] = result.timing.wns
        if result.timing.tns is not None:
            metrics["tns_ns"] = result.timing.tns
        if result.timing.num_violating_paths is not None:
            metrics["violating_paths"] = result.timing.num_violating_paths
        if result.area.utilization is not None:
            metrics["utilization"] = result.area.utilization
        if result.area.cell_area is not None:
            metrics["cell_area"] = result.area.cell_area
        if result.power.total_power_mw is not None:
            metrics["total_power_mw"] = result.power.total_power_mw
        if result.power.leakage_power_mw is not None:
            metrics["leakage_power_mw"] = result.power.leakage_power_mw
        if result.route.drc_errors is not None:
            metrics["route_drc_errors"] = result.route.drc_errors
        if result.route.congestion_h is not None:
            metrics["congestion_h"] = result.route.congestion_h
        if result.route.congestion_v is not None:
            metrics["congestion_v"] = result.route.congestion_v
        if result.drc.total_errors is not None:
            metrics["pv_drc_errors"] = result.drc.total_errors
        if result.drc.is_clean:
            metrics["drc_clean"] = True
        if result.lvs.is_clean:
            metrics["lvs_clean"] = True

        return metrics

    def _compute_deltas(
        self,
        name_before: str, result_before: StageResult,
        name_after: str, result_after: StageResult,
    ) -> list[QoRDelta]:
        """Compute metric deltas between two stages."""
        deltas = []

        # WNS
        wns_b = result_before.timing.wns
        wns_a = result_after.timing.wns
        if wns_b is not None and wns_a is not None:
            d = wns_a - wns_b
            regression = d < -0.05  # more than 50ps worse
            deltas.append(QoRDelta(
                metric_name="WNS",
                stage_before=name_before,
                stage_after=name_after,
                value_before=wns_b,
                value_after=wns_a,
                delta=d,
                is_regression=regression,
                comment=f"{'Regression' if regression else 'OK'}: {d:+.4f}ns",
            ))

        # TNS
        tns_b = result_before.timing.tns
        tns_a = result_after.timing.tns
        if tns_b is not None and tns_a is not None:
            d = tns_a - tns_b
            regression = d < -0.5
            deltas.append(QoRDelta(
                metric_name="TNS",
                stage_before=name_before,
                stage_after=name_after,
                value_before=tns_b,
                value_after=tns_a,
                delta=d,
                is_regression=regression,
                comment=f"{'Regression' if regression else 'OK'}: {d:+.4f}ns",
            ))

        # Utilization
        util_b = result_before.area.utilization
        util_a = result_after.area.utilization
        if util_b is not None and util_a is not None:
            d = util_a - util_b
            regression = d > 0.1  # >10% increase
            deltas.append(QoRDelta(
                metric_name="Utilization",
                stage_before=name_before,
                stage_after=name_after,
                value_before=util_b,
                value_after=util_a,
                delta=d,
                is_regression=regression,
                comment=f"Utilization change: {d:+.1%}",
            ))

        return deltas

    def _recommend_fix(self, delta: QoRDelta, result: StageResult) -> list[str]:
        """Generate recommendations based on a regression."""
        recs = []

        if delta.metric_name == "WNS" and delta.is_regression:
            if delta.stage_after.lower() == "placement":
                recs.append("Consider increasing placement effort or enabling CCD")
                recs.append("Check congestion — high congestion causes timing degradation")
            elif delta.stage_after.lower() == "cts":
                recs.append("Review clock tree structure — excessive skew or insertion delay")
                recs.append("Consider useful skew or clock tree restructuring")
            elif delta.stage_after.lower() in ("routing", "route_opt"):
                recs.append("Route timing degradation — check for congestion-induced detours")
                recs.append("Consider increasing max routing layer or reducing density")

        if delta.metric_name == "TNS" and delta.is_regression:
            recs.append(f"TNS degraded by {abs(delta.delta):.2f}ns — focus on worst path groups")

        if delta.metric_name == "Utilization" and delta.is_regression:
            recs.append("Utilization increased significantly — consider enlarging die or reducing logic")

        return recs

    def _build_summary(
        self,
        stage_metrics: dict[str, dict[str, Any]],
        deltas: list[QoRDelta],
    ) -> str:
        """Build a human-readable summary."""
        lines = [f"QoR Analysis: {self.state.config.design_name}", ""]

        # Stage-by-stage metrics
        for stage_name, metrics in stage_metrics.items():
            lines.append(f"[{stage_name}]")
            for k, v in metrics.items():
                if isinstance(v, float):
                    lines.append(f"  {k}: {v:.4f}")
                else:
                    lines.append(f"  {k}: {v}")
            lines.append("")

        # Regressions
        regressions = [d for d in deltas if d.is_regression]
        if regressions:
            lines.append("REGRESSIONS DETECTED:")
            for r in regressions:
                lines.append(f"  {r.metric_name}: {r.stage_before} -> {r.stage_after}: {r.comment}")
        else:
            lines.append("No significant regressions detected.")

        return "\n".join(lines)

    def report(self, output_path: str | Path | None = None) -> str:
        """Generate and optionally save a QoR report."""
        diagnosis = self.analyze()
        text = diagnosis.summary

        if diagnosis.recommendations:
            text += "\n\nRECOMMENDATIONS:\n"
            for i, rec in enumerate(diagnosis.recommendations, 1):
                text += f"  {i}. {rec}\n"

        if output_path:
            Path(output_path).write_text(text)

        return text
