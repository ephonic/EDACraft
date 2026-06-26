"""Reusable transaction recipe definitions.

This module is intentionally small: it keeps recipe semantics in one place
while execution remains in ``skill_ppa``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from rtlgen.contracts import PerfCheck, PerfScenario, PerfStimulusRecipe, PerfStimulusStep, TransactionContract


@dataclass(frozen=True)
class TransactionRecipeSpec:
    """Declarative recipe metadata for contract-driven perf checks."""

    name: str
    check_suffix: str
    check_kind: str
    description: str
    default_source_event: str = "level"
    default_sink_event: str = "level"
    scenario_template: str = "pulse"
    required_metadata_keys: Tuple[str, ...] = ()
    require_max_cycles: bool = False
    requires_trigger_qualifier_on_handshake: bool = True
    requires_completion_qualifier_on_handshake: bool = True
    max_value_metadata_key: str = ""
    max_value_no_overlap: float = 1.0
    max_value_allow_overlap: float = 2.0


TRANSACTION_RECIPE_REGISTRY: Dict[str, TransactionRecipeSpec] = {
    "ready_valid_transfer": TransactionRecipeSpec(
        name="ready_valid_transfer",
        check_suffix="accept_latency",
        check_kind="latency",
        description="Derived ready/valid accept latency",
        default_source_event="rise",
        default_sink_event="level",
        scenario_template="pulse",
        require_max_cycles=True,
    ),
    "request_grant_completion": TransactionRecipeSpec(
        name="request_grant_completion",
        check_suffix="latency",
        check_kind="latency",
        description="Derived request-to-completion latency",
        default_source_event="rise",
        default_sink_event="rise",
        scenario_template="pulse",
        require_max_cycles=True,
    ),
    "single_outstanding_response": TransactionRecipeSpec(
        name="single_outstanding_response",
        check_suffix="outstanding",
        check_kind="completion_bound",
        description="Derived outstanding-response bound",
        default_source_event="handshake",
        default_sink_event="rise",
        scenario_template="periodic_issue",
        required_metadata_keys=("max_outstanding",),
        max_value_metadata_key="max_outstanding",
        max_value_no_overlap=1.0,
        max_value_allow_overlap=2.0,
    ),
    "ordered_completion": TransactionRecipeSpec(
        name="ordered_completion",
        check_suffix="outstanding",
        check_kind="completion_bound",
        description="Derived ordered-completion outstanding bound",
        default_source_event="rise",
        default_sink_event="rise",
        scenario_template="periodic_issue",
        required_metadata_keys=("max_outstanding",),
        max_value_metadata_key="max_outstanding",
        max_value_no_overlap=1.0,
        max_value_allow_overlap=2.0,
    ),
    "bounded_queue_occupancy": TransactionRecipeSpec(
        name="bounded_queue_occupancy",
        check_suffix="occupancy",
        check_kind="occupancy",
        description="Derived bounded queue occupancy",
        default_source_event="level",
        default_sink_event="level",
        scenario_template="hold_trigger",
        required_metadata_keys=("max_value",),
    ),
    "backpressure_hold": TransactionRecipeSpec(
        name="backpressure_hold",
        check_suffix="stall_ratio",
        check_kind="stall_ratio",
        description="Derived backpressure hold ratio",
        default_source_event="level",
        default_sink_event="level",
        scenario_template="hold_trigger",
        required_metadata_keys=("max_ratio",),
    ),
}


def supported_transaction_recipes(include_empty: bool = False) -> Set[str]:
    """Return supported transaction recipe names."""

    names = set(TRANSACTION_RECIPE_REGISTRY)
    if include_empty:
        names.add("")
    return names


def transaction_perf_check_name(txn: TransactionContract, suffix: str) -> str:
    """Canonical name for a check derived from a transaction."""

    return f"txn_{txn.name}_{suffix}"


def get_transaction_recipe(recipe: str) -> Optional[TransactionRecipeSpec]:
    """Look up a transaction recipe definition."""

    return TRANSACTION_RECIPE_REGISTRY.get(recipe)


def validate_transaction_recipe_contract(txn: TransactionContract) -> List[str]:
    """Validate recipe-specific requirements for a transaction contract."""

    issues: List[str] = []
    recipe_name = getattr(txn, "recipe", "")
    if not recipe_name:
        return issues
    spec = get_transaction_recipe(recipe_name)
    if spec is None:
        issues.append(f"transaction {txn.name}: unsupported recipe {recipe_name}")
        return issues

    if not txn.trigger_signals:
        issues.append(f"transaction {txn.name}: recipe {recipe_name} requires trigger_signals")
    if not txn.completion_signals:
        issues.append(f"transaction {txn.name}: recipe {recipe_name} requires completion_signals")
    trigger_event = getattr(txn, "trigger_event", spec.default_source_event) or spec.default_source_event
    completion_event = getattr(txn, "completion_event", spec.default_sink_event) or spec.default_sink_event
    if (
        trigger_event == "handshake"
        and spec.requires_trigger_qualifier_on_handshake
        and not getattr(txn, "trigger_qualifiers", [])
    ):
        issues.append(f"transaction {txn.name}: recipe {recipe_name} handshake trigger requires trigger_qualifiers")
    if (
        completion_event == "handshake"
        and spec.requires_completion_qualifier_on_handshake
        and not getattr(txn, "completion_qualifiers", [])
    ):
        issues.append(
            f"transaction {txn.name}: recipe {recipe_name} handshake completion requires completion_qualifiers"
        )
    if spec.require_max_cycles and txn.max_cycles is None:
        issues.append(f"transaction {txn.name}: recipe {recipe_name} requires max_cycles")
    metadata = dict(getattr(txn, "metadata", {}))
    missing_metadata = [key for key in spec.required_metadata_keys if key not in metadata]
    if missing_metadata:
        issues.append(
            f"transaction {txn.name}: recipe {recipe_name} requires metadata "
            f"{', '.join(missing_metadata)}"
        )
    return issues


def _scenario_base_stimulus(txn: TransactionContract, trigger_signal: str, trigger_idle: int) -> Dict[str, int]:
    stimulus: Dict[str, int] = {trigger_signal: trigger_idle}
    for qualifier in list(getattr(txn, "trigger_qualifiers", [])) + list(
        getattr(txn, "completion_qualifiers", [])
    ):
        if qualifier and qualifier not in stimulus:
            stimulus[qualifier] = int(txn.metadata.get(f"{qualifier}_default", 1))
    return stimulus


def _scenario_active_values(txn: TransactionContract, trigger_signal: str) -> Dict[str, int]:
    values: Dict[str, int] = {trigger_signal: 1}
    for qualifier in getattr(txn, "trigger_qualifiers", []):
        if qualifier:
            values[qualifier] = int(txn.metadata.get(f"{qualifier}_active", 1))
    return values


def _scenario_expected_observations(txn: TransactionContract, spec: TransactionRecipeSpec) -> Dict[str, str]:
    return {
        "transaction_name": txn.name,
        "transaction_recipe": spec.name,
        "scenario_template": spec.scenario_template,
    }


def _scenario_tags(spec: TransactionRecipeSpec, *extra: str) -> List[str]:
    tags = ["auto", "transaction_recipe", spec.name, f"template:{spec.scenario_template}"]
    tags.extend(item for item in extra if item)
    return tags


def _metadata_int(txn: TransactionContract, key: str, default: int = 0) -> int:
    try:
        return int(txn.metadata.get(key, default))
    except (TypeError, ValueError):
        return default


def _metadata_bool(txn: TransactionContract, key: str, default: bool = False) -> bool:
    value = txn.metadata.get(key, default)
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


def _scenario_timeline_steps(txn: TransactionContract, trigger_signal: str, cycles: int) -> List[PerfStimulusStep]:
    steps: List[PerfStimulusStep] = []
    delay_cycles = max(_metadata_int(txn, "scenario_delay_cycles", 0), 0)
    if delay_cycles > 0:
        completion_values = {
            signal: int(txn.metadata.get(f"{signal}_delayed_value", 1))
            for signal in getattr(txn, "completion_signals", [])[:1]
            if signal
        }
        for qualifier in getattr(txn, "completion_qualifiers", []):
            if qualifier:
                completion_values[qualifier] = int(txn.metadata.get(f"{qualifier}_active", 1))
        if completion_values:
            steps.append(
                PerfStimulusStep(
                    start_cycle=min(delay_cycles, max(cycles - 1, 0)),
                    values=completion_values,
                    description="Drive delayed completion observation for the transaction recipe.",
                )
            )

    backpressure_signal = str(txn.metadata.get("backpressure_signal", "") or "")
    if backpressure_signal:
        start = max(_metadata_int(txn, "backpressure_start_cycle", 1), 0)
        default_end = min(start + max(_metadata_int(txn, "backpressure_cycles", 2), 1) - 1, cycles - 1)
        end = min(_metadata_int(txn, "backpressure_end_cycle", default_end), cycles - 1)
        steps.append(
            PerfStimulusStep(
                start_cycle=start,
                end_cycle=max(start, end),
                values={backpressure_signal: int(txn.metadata.get("backpressure_value", 1))},
                description="Drive a configured backpressure window for the transaction recipe.",
            )
        )

    if _metadata_bool(txn, "violation_probe", False):
        start = max(_metadata_int(txn, "violation_probe_start_cycle", 0), 0)
        pulse_count = max(_metadata_int(txn, "violation_probe_pulses", 3), 1)
        for offset in range(pulse_count):
            cycle = min(start + offset, max(cycles - 1, 0))
            steps.append(
                PerfStimulusStep(
                    start_cycle=cycle,
                    values={trigger_signal: 1},
                    description="Issue an outstanding-boundary probe trigger.",
                )
            )
    return steps


def _scenario_extra_tags(txn: TransactionContract) -> List[str]:
    tags: List[str] = []
    if _metadata_int(txn, "scenario_delay_cycles", 0) > 0:
        tags.append("delayed_completion")
    if txn.metadata.get("backpressure_signal"):
        tags.append("backpressure_window")
    if _metadata_bool(txn, "violation_probe", False):
        tags.append("outstanding_violation_probe")
    return tags


def _scenario_expected_with_metadata(
    txn: TransactionContract,
    spec: TransactionRecipeSpec,
) -> Dict[str, object]:
    expected: Dict[str, object] = _scenario_expected_observations(txn, spec)
    if _metadata_int(txn, "scenario_delay_cycles", 0) > 0:
        expected["scenario_delay_cycles"] = _metadata_int(txn, "scenario_delay_cycles", 0)
    if txn.metadata.get("backpressure_signal"):
        expected["backpressure_signal"] = str(txn.metadata.get("backpressure_signal"))
    if _metadata_bool(txn, "violation_probe", False):
        expected["violation_probe"] = True
    return expected


def derive_transaction_perf_check(txn: TransactionContract) -> Optional[PerfCheck]:
    """Derive the canonical perf check for a transaction recipe."""

    recipe_name = getattr(txn, "recipe", "")
    spec = get_transaction_recipe(recipe_name)
    if spec is None:
        return None

    common_meta = {
        "transaction_name": txn.name,
        "transaction_recipe": recipe_name,
    }
    sample_cycles = max(int(getattr(txn, "sample_cycles", 0) or 0), 0)
    check = PerfCheck(
        name=transaction_perf_check_name(txn, spec.check_suffix),
        kind=spec.check_kind,
        description=txn.description or f"{spec.description} for {txn.name}.",
        source_signals=list(txn.trigger_signals[:1]),
        sink_signals=list(txn.completion_signals[:1]),
        source_event=getattr(txn, "trigger_event", spec.default_source_event) or spec.default_source_event,
        sink_event=getattr(txn, "completion_event", spec.default_sink_event) or spec.default_sink_event,
        source_qualifiers=list(getattr(txn, "trigger_qualifiers", [])),
        sink_qualifiers=list(getattr(txn, "completion_qualifiers", [])),
        max_cycles=txn.max_cycles,
        sample_cycles=sample_cycles,
        metadata=dict(common_meta),
    )

    if spec.check_kind == "completion_bound":
        default_max = spec.max_value_allow_overlap if txn.allow_overlap else spec.max_value_no_overlap
        check.max_value = float(txn.metadata.get(spec.max_value_metadata_key, default_max))
        check.max_cycles = None
    elif spec.check_kind == "occupancy":
        if "min_value" in txn.metadata:
            check.min_value = float(txn.metadata["min_value"])
        if "max_value" in txn.metadata:
            check.max_value = float(txn.metadata["max_value"])
    elif spec.check_kind == "stall_ratio":
        if "max_ratio" in txn.metadata:
            check.max_ratio = float(txn.metadata["max_ratio"])

    return check


def derive_transaction_scenario(txn: TransactionContract) -> Optional[PerfScenario]:
    """Derive a minimal stimulus scenario for a transaction recipe."""

    recipe_name = getattr(txn, "recipe", "")
    spec = get_transaction_recipe(recipe_name)
    if spec is None:
        return None

    trigger_signal = txn.trigger_signals[0] if txn.trigger_signals else ""
    if not trigger_signal:
        return None

    sample_cycles = max(int(getattr(txn, "sample_cycles", 0) or 0), 4)
    if spec.scenario_template == "periodic_issue":
        cycles = max(sample_cycles, 8)
        base_stimulus = _scenario_base_stimulus(txn, trigger_signal, 0)
        active_values = _scenario_active_values(txn, trigger_signal)
        timeline_steps = _scenario_timeline_steps(txn, trigger_signal, cycles)
        return PerfScenario(
            name=f"auto_{txn.name}_{recipe_name}",
            description=f"Auto-generated minimal scenario for {recipe_name} transaction {txn.name}.",
            stimulus=base_stimulus,
            stimulus_recipes=[
                PerfStimulusRecipe(
                    kind="periodic",
                    values=active_values,
                    start_cycle=0,
                    end_cycle=cycles - 1,
                    period=2,
                    duty_cycles=1,
                    description="Issue one-cycle transaction triggers every two cycles.",
                )
            ],
            stimulus_timeline=timeline_steps,
            linked_transactions=[txn.name],
            cycles=cycles,
            expected_observations=_scenario_expected_with_metadata(txn, spec),
            tags=_scenario_tags(spec, "multi_issue", *_scenario_extra_tags(txn)),
        )

    if spec.scenario_template == "hold_trigger":
        cycles = max(sample_cycles, 4)
        base_stimulus = _scenario_base_stimulus(txn, trigger_signal, 1)
        timeline_steps = _scenario_timeline_steps(txn, trigger_signal, cycles)
        return PerfScenario(
            name=f"auto_{txn.name}_{recipe_name}",
            description=f"Auto-generated minimal scenario for {recipe_name} transaction {txn.name}.",
            stimulus=base_stimulus,
            stimulus_timeline=timeline_steps,
            linked_transactions=[txn.name],
            cycles=cycles,
            expected_observations=_scenario_expected_with_metadata(txn, spec),
            tags=_scenario_tags(spec, "sustained_window", *_scenario_extra_tags(txn)),
        )

    cycles = max(sample_cycles, int(getattr(txn, "max_cycles", 0) or 0) + 2, 4)
    base_stimulus = _scenario_base_stimulus(txn, trigger_signal, 0)
    active_values = _scenario_active_values(txn, trigger_signal)
    timeline_steps = _scenario_timeline_steps(txn, trigger_signal, cycles)
    return PerfScenario(
        name=f"auto_{txn.name}_{recipe_name}",
        description=f"Auto-generated minimal scenario for {recipe_name} transaction {txn.name}.",
        stimulus=base_stimulus,
        stimulus_recipes=[
            PerfStimulusRecipe(
                kind="pulse",
                values=active_values,
                start_cycle=0,
                description="Issue one transaction trigger pulse.",
            )
        ],
        stimulus_timeline=timeline_steps,
        linked_transactions=[txn.name],
        cycles=cycles,
        expected_observations=_scenario_expected_with_metadata(txn, spec),
        tags=_scenario_tags(spec, "single_issue", *_scenario_extra_tags(txn)),
    )
