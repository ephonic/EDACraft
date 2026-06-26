"""Reusable protocol recipe definitions.

Protocol recipes describe persistent interface behavior. They complement
transaction recipes, which describe one bounded transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from rtlgen.contracts import PerfCheck, PerfScenario, ProtocolContract


@dataclass(frozen=True)
class ProtocolRecipeSpec:
    """Declarative metadata for protocol-level perf checks."""

    name: str
    check_suffix: str
    check_kind: str
    description: str
    kind_aliases: Tuple[str, ...] = ()
    required_request_signals: bool = True
    required_response_signals: bool = False
    required_flow_control_signals: bool = False
    required_metadata_keys: Tuple[str, ...] = ()


PROTOCOL_RECIPE_REGISTRY: Dict[str, ProtocolRecipeSpec] = {
    "ready_valid_backpressure": ProtocolRecipeSpec(
        name="ready_valid_backpressure",
        check_suffix="backpressure_ratio",
        check_kind="stall_ratio",
        description="Derived ready/valid backpressure ratio",
        kind_aliases=("ready_valid", "valid_ready", "ready_valid_stream"),
        required_flow_control_signals=True,
        required_metadata_keys=("max_ratio",),
    ),
    "ready_valid_no_drop_no_duplicate": ProtocolRecipeSpec(
        name="ready_valid_no_drop_no_duplicate",
        check_suffix="no_drop_no_duplicate",
        check_kind="completion_bound",
        description="Derived ready/valid no-drop/no-duplicate outstanding bound",
        kind_aliases=("ready_valid", "valid_ready", "ready_valid_stream"),
        required_response_signals=True,
        required_metadata_keys=("max_outstanding",),
    ),
}


def supported_protocol_recipes(include_empty: bool = False) -> Set[str]:
    names = set(PROTOCOL_RECIPE_REGISTRY)
    if include_empty:
        names.add("")
    return names


def protocol_perf_check_name(proto: ProtocolContract, suffix: str) -> str:
    return f"proto_{proto.name}_{suffix}"


def get_protocol_recipe(recipe: str) -> Optional[ProtocolRecipeSpec]:
    return PROTOCOL_RECIPE_REGISTRY.get(recipe)


def infer_protocol_recipe(proto: ProtocolContract) -> str:
    recipe = getattr(proto, "recipe", "") or ""
    if recipe:
        return recipe
    metadata = dict(getattr(proto, "metadata", {}))
    if metadata.get("protocol_recipe"):
        return str(metadata["protocol_recipe"])
    return ""


def validate_protocol_recipe_contract(proto: ProtocolContract) -> List[str]:
    issues: List[str] = []
    recipe_name = infer_protocol_recipe(proto)
    if not recipe_name:
        return issues
    spec = get_protocol_recipe(recipe_name)
    if spec is None:
        issues.append(f"protocol {proto.name}: unsupported recipe {recipe_name}")
        return issues
    if spec.required_request_signals and not getattr(proto, "request_signals", []):
        issues.append(f"protocol {proto.name}: recipe {recipe_name} requires request_signals")
    if spec.required_response_signals and not getattr(proto, "response_signals", []):
        issues.append(f"protocol {proto.name}: recipe {recipe_name} requires response_signals")
    if spec.required_flow_control_signals and not getattr(proto, "flow_control_signals", []):
        issues.append(f"protocol {proto.name}: recipe {recipe_name} requires flow_control_signals")
    metadata = dict(getattr(proto, "metadata", {}))
    missing_metadata = [key for key in spec.required_metadata_keys if key not in metadata]
    if missing_metadata:
        issues.append(
            f"protocol {proto.name}: recipe {recipe_name} requires metadata "
            f"{', '.join(missing_metadata)}"
        )
    return issues


def derive_protocol_perf_check(proto: ProtocolContract) -> Optional[PerfCheck]:
    recipe_name = infer_protocol_recipe(proto)
    spec = get_protocol_recipe(recipe_name)
    if spec is None:
        return None

    metadata = {
        "protocol_name": proto.name,
        "protocol_recipe": recipe_name,
    }
    metadata.update(dict(getattr(proto, "metadata", {})))
    check = PerfCheck(
        name=protocol_perf_check_name(proto, spec.check_suffix),
        kind=spec.check_kind,
        description=proto.description or f"{spec.description} for {proto.name}.",
        source_signals=list(proto.request_signals[:1]),
        sink_signals=list((proto.flow_control_signals if spec.check_kind == "stall_ratio" else proto.response_signals)[:1]),
        source_event=str(proto.metadata.get("source_event", "level")),
        sink_event=str(proto.metadata.get("sink_event", "level")),
        max_cycles=proto.metadata.get("max_cycles"),
        sample_cycles=int(proto.metadata.get("sample_cycles", 8) or 8),
        metadata=metadata,
    )
    if spec.check_kind == "stall_ratio":
        check.max_ratio = float(proto.metadata.get("max_ratio", 1.0))
    elif spec.check_kind == "completion_bound":
        check.max_value = float(proto.metadata.get("max_outstanding", 1.0))
        check.source_event = str(proto.metadata.get("source_event", "rise"))
        check.sink_event = str(proto.metadata.get("sink_event", "rise"))
    return check


def derive_protocol_scenario(proto: ProtocolContract) -> Optional[PerfScenario]:
    check = derive_protocol_perf_check(proto)
    if check is None or not check.source_signals:
        return None
    source = check.source_signals[0]
    stimulus = {source: int(proto.metadata.get(f"{source}_default", 1))}
    for sig in getattr(proto, "flow_control_signals", []):
        stimulus[sig] = int(proto.metadata.get(f"{sig}_default", 1))
    cycles = max(int(proto.metadata.get("sample_cycles", check.sample_cycles) or check.sample_cycles), 4)
    return PerfScenario(
        name=f"auto_{proto.name}_{check.metadata['protocol_recipe']}",
        description=f"Auto-generated minimal scenario for protocol recipe {check.metadata['protocol_recipe']}.",
        stimulus=stimulus,
        linked_checks=[check.name],
        cycles=cycles,
        expected_observations={
            "protocol_name": proto.name,
            "protocol_recipe": check.metadata["protocol_recipe"],
        },
        tags=["auto", "protocol_recipe", check.metadata["protocol_recipe"]],
    )
