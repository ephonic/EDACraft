import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

loaded_rtlgen = sys.modules.get("rtlgen")
loaded_path = Path(getattr(loaded_rtlgen, "__file__", "")).resolve() if loaded_rtlgen else None
local_init = REPO_ROOT / "rtlgen" / "__init__.py"
if loaded_path and loaded_path != local_init:
    for name in list(sys.modules):
        if name == "rtlgen" or name.startswith("rtlgen."):
            sys.modules.pop(name, None)

from rtlgen import (
    AgentDSLGenerator,
    ArchitectureIR,
    ArchitecturePlanner,
    BehavioralSpec,
    Const,
    CycleIR,
    CycleTransactionIR,
    DSLGenerator,
    DSLSimValidator,
    FunctionSpec,
    Input,
    IRConnectionSpec,
    InterfaceSpec,
    Output,
    PPASpec,
    PortSpec,
    Simulator,
    SpecCompleter,
    SpecIR,
    SubmoduleInstanceSpec,
    TimingSpec,
    TransactionEventIR,
    TransactionIR,
    Verifier,
    VerificationPlanIR,
    VerificationSpec,
    VerilogEmitter,
    generate_dsl_skeleton,
)
from rtlgen.spec_ir import IR_SCHEMA_VERSION
from rtlgen.arch_def import AgentPackage, ArchDefinition, PortDesc, ProcessingElement
from rtlgen.contracts import (
    FunctionalObjective,
    Layer,
    ModuleContract,
    PerfCheck,
    PerfScenario,
    PerfStimulusRecipe,
    PerfStimulusStep,
    PerformanceObjective,
    PortContract,
    ProtocolContract,
    TransactionContract,
)
from rtlgen.core import Module, Input, Output, Reg
from rtlgen.logic import If, Else, Mux
from rtlgen.gen_requirement import GenerationContext, ModuleRequirement, SubModuleInfo
from rtlgen.prompt_builder import build_generation_prompt
from rtlgen.skill_ppa import SkillPPARunner
from rtlgen.transaction_recipes import (
    derive_transaction_perf_check,
    derive_transaction_scenario,
    supported_transaction_recipes,
    validate_transaction_recipe_contract,
)
from rtlgen.protocol_recipes import (
    derive_protocol_perf_check,
    derive_protocol_scenario,
    supported_protocol_recipes,
    validate_protocol_recipe_contract,
)


def _mac_spec() -> SpecIR:
    return SpecIR(
        name="MacPipe",
        category="stream_pipeline",
        function=FunctionSpec(expr="y = a * b + c"),
        ports=[
            PortSpec(name="a", direction="input", width=16),
            PortSpec(name="b", direction="input", width=16),
            PortSpec(name="c", direction="input", width=32),
            PortSpec(name="y", direction="output", width=32),
        ],
        timing=TimingSpec(latency_max=3),
        ppa=PPASpec(priority="timing_first"),
    )


def _dummy_agent_package() -> AgentPackage:
    pe = ProcessingElement(
        name="mac0",
        pe_type="mac",
        inputs=[
            PortDesc(name="a", direction="input", width=16),
            PortDesc(name="b", direction="input", width=16),
            PortDesc(name="c", direction="input", width=32),
        ],
        outputs=[PortDesc(name="y", direction="output", width=32)],
    )
    return AgentPackage(pe=pe, behavioral_reference=lambda ctx: None)


def _adder_behavior_package() -> AgentPackage:
    pe = ProcessingElement(
        name="adder0",
        pe_type="adder",
        inputs=[
            PortDesc(name="a", direction="input", width=8),
            PortDesc(name="b", direction="input", width=8),
        ],
        outputs=[PortDesc(name="y", direction="output", width=9)],
    )

    def behavior(ctx):
        ctx.set_output("y", ctx.get_input("a", 0) + ctx.get_input("b", 0))

    pkg = AgentPackage(
        pe=pe,
        behavioral_reference=behavior,
        golden_tests=[{"inputs": {"a": 3, "b": 4}, "expected_outputs": {"y": 7}}],
    )
    pkg._behavior_requirement = {
        "interfaces": [],
        "control_patterns": [],
        "datapath_patterns": ["alu_execute"],
    }
    return pkg


class _PerfScenarioDemo(Module):
    def __init__(self):
        super().__init__("perf_scenario_demo")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req = Input(1, "req")
        self.ack = Output(1, "ack")
        self.pending = Reg(1, "pending")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.pending <<= 0
            with Else():
                self.pending <<= self.req

        with self.comb:
            self.ack <<= self.pending

        self._module_contract = ModuleContract(
            module_name="PerfScenarioDemo",
            role="Test-only contract demo for scenario-driven perf verification.",
            layer=Layer.L3_DSL,
            ports=[
                PortContract(name="clk", direction="input", width=1),
                PortContract(name="rst_n", direction="input", width=1),
                PortContract(name="req", direction="input", width=1),
                PortContract(name="ack", direction="output", width=1),
            ],
            state_elements=["pending"],
            functional_objectives=[
                FunctionalObjective(
                    name="req_ack_pipeline",
                    description="A request should appear as an ack one cycle later.",
                )
            ],
            performance_objective=PerformanceObjective(
                checks=[
                    PerfCheck(
                        name="ack_latency",
                        kind="latency",
                        description="Ack should appear within one cycle of request assertion.",
                        source_signals=["req"],
                        sink_signals=["ack"],
                        max_cycles=1,
                        sample_cycles=4,
                    ),
                    PerfCheck(
                        name="ack_rate",
                        kind="throughput",
                        description="Ack should stay active across the sustained request phase.",
                        source_signals=["req"],
                        sink_signals=["ack"],
                        min_rate=0.50,
                        sample_cycles=4,
                    ),
                ],
                scenarios=[
                    PerfScenario(
                        name="timeline_req",
                        description="Drive req low first, then hold it high for the remainder of the sample window.",
                        stimulus={"req": 0},
                        stimulus_timeline=[
                            PerfStimulusStep(
                                start_cycle=1,
                                end_cycle=3,
                                values={"req": 1},
                                description="Raise req after the first observed cycle.",
                            )
                        ],
                        linked_checks=["ack_latency", "ack_rate"],
                        expected_observations={},
                        cycles=4,
                    )
                ],
            ),
        )


class _PerfRichChecksDemo(Module):
    def __init__(self):
        super().__init__("perf_rich_checks_demo")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req = Input(1, "req")
        self.slot0_fire = Output(1, "slot0_fire")
        self.slot1_fire = Output(1, "slot1_fire")
        self.occupancy = Output(3, "occupancy")
        self.done = Output(1, "done")
        self.phase = Reg(3, "phase")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.phase <<= 0
            with Else():
                self.phase <<= self.phase + self.req

        with self.comb:
            self.slot0_fire <<= self.req & ~self.phase[0]
            self.slot1_fire <<= self.req & self.phase[0]
            self.done <<= self.req & (self.phase != 0)
            self.occupancy <<= Mux(self.req, Const(2, 3), Const(0, 3))

        self._module_contract = ModuleContract(
            module_name="PerfRichChecksDemo",
            role="Test-only module that exercises richer dynamic perf checks.",
            layer=Layer.L3_DSL,
            ports=[
                PortContract(name="clk", direction="input", width=1),
                PortContract(name="rst_n", direction="input", width=1),
                PortContract(name="req", direction="input", width=1),
                PortContract(name="slot0_fire", direction="output", width=1),
                PortContract(name="slot1_fire", direction="output", width=1),
                PortContract(name="occupancy", direction="output", width=3),
                PortContract(name="done", direction="output", width=1),
            ],
            performance_objective=PerformanceObjective(
                checks=[
                    PerfCheck(
                        name="rich_occupancy",
                        kind="occupancy",
                        description="Average occupancy should be non-zero and peak bounded.",
                        sink_signals=["occupancy"],
                        min_value=1.0,
                        max_value=2.0,
                        sample_cycles=4,
                    ),
                    PerfCheck(
                        name="rich_completion_bound",
                        kind="completion_bound",
                        description="Requests should not outpace completions by more than one event.",
                        source_signals=["req"],
                        sink_signals=["done"],
                        source_event="rise",
                        sink_event="rise",
                        max_value=1.0,
                        sample_cycles=4,
                    ),
                    PerfCheck(
                        name="rich_fairness",
                        kind="fairness",
                        description="Alternating slot fires should remain balanced.",
                        sink_signals=["slot0_fire", "slot1_fire"],
                        min_ratio=0.50,
                        sample_cycles=4,
                        metadata={
                            "sink_groups": [
                                {"name": "slot0", "signals": ["slot0_fire"]},
                                {"name": "slot1", "signals": ["slot1_fire"]},
                            ]
                        },
                    ),
                ],
                scenarios=[
                    PerfScenario(
                        name="rich_scenario",
                        description="Hold req high throughout the observation window.",
                        stimulus={"req": 1},
                        linked_checks=["rich_occupancy", "rich_completion_bound", "rich_fairness"],
                        cycles=4,
                    )
                ],
            ),
        )


class _PerfHandshakeDemo(Module):
    def __init__(self):
        super().__init__("perf_handshake_demo")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.done = Output(1, "done")
        self.accepted_d = Reg(1, "accepted_d")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.accepted_d <<= 0
            with Else():
                self.accepted_d <<= self.valid_in

        with self.comb:
            self.ready_out <<= 1
            self.done <<= self.accepted_d

        self._module_contract = ModuleContract(
            module_name="PerfHandshakeDemo",
            role="Test-only module for handshake-event and recipe-driven perf checks.",
            layer=Layer.L3_DSL,
            ports=[
                PortContract(name="clk", direction="input", width=1),
                PortContract(name="rst_n", direction="input", width=1),
                PortContract(name="valid_in", direction="input", width=1),
                PortContract(name="ready_out", direction="output", width=1),
                PortContract(name="done", direction="output", width=1),
            ],
            transactions=[
                TransactionContract(
                    name="accepted_valid_to_done",
                    trigger_signals=["valid_in"],
                    completion_signals=["done"],
                    recipe="single_outstanding_response",
                    trigger_event="handshake",
                    trigger_qualifiers=["ready_out"],
                    completion_event="rise",
                    sample_cycles=8,
                    description="Accepted valid pulses should retire with bounded outstanding depth.",
                    metadata={"max_outstanding": 1},
                )
            ],
            performance_objective=PerformanceObjective(
                scenarios=[
                    PerfScenario(
                        name="periodic_handshakes",
                        description="Generate one valid pulse every other cycle using a periodic recipe.",
                        stimulus={"valid_in": 0},
                        stimulus_recipes=[
                            PerfStimulusRecipe(
                                kind="periodic",
                                start_cycle=0,
                                end_cycle=7,
                                period=2,
                                duty_cycles=1,
                                values={"valid_in": 1},
                                description="Issue one-cycle valid pulses every two cycles.",
                            )
                        ],
                        linked_transactions=["accepted_valid_to_done"],
                        cycles=8,
                    )
                ],
            ),
        )


class _PerfInputQualifierDemo(Module):
    def __init__(self):
        super().__init__("perf_input_qualifier_demo")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_in = Input(1, "valid_in")
        self.ready_in = Input(1, "ready_in")
        self.done = Output(1, "done")
        self.accepted_d = Reg(1, "accepted_d")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.accepted_d <<= 0
            with Else():
                self.accepted_d <<= self.valid_in & self.ready_in

        with self.comb:
            self.done <<= self.accepted_d

        self._module_contract = ModuleContract(
            module_name="PerfInputQualifierDemo",
            role="Test-only module for auto scenario input qualifier driving.",
            layer=Layer.L3_DSL,
            ports=[
                PortContract(name="clk", direction="input", width=1),
                PortContract(name="rst_n", direction="input", width=1),
                PortContract(name="valid_in", direction="input", width=1),
                PortContract(name="ready_in", direction="input", width=1),
                PortContract(name="done", direction="output", width=1),
            ],
            transactions=[
                TransactionContract(
                    name="accepted_input_to_done",
                    trigger_signals=["valid_in"],
                    completion_signals=["done"],
                    recipe="single_outstanding_response",
                    trigger_event="handshake",
                    trigger_qualifiers=["ready_in"],
                    completion_event="rise",
                    sample_cycles=8,
                    description="Accepted valid/ready inputs should retire with bounded outstanding depth.",
                    metadata={"max_outstanding": 1},
                )
            ],
            performance_objective=PerformanceObjective(scenarios=[]),
        )


class _PerfProtocolDemo(Module):
    def __init__(self):
        super().__init__("perf_protocol_demo")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")

        with self.comb:
            self.ready_out <<= 0

        self._module_contract = ModuleContract(
            module_name="PerfProtocolDemo",
            role="Test-only module for protocol recipe perf checks.",
            layer=Layer.L3_DSL,
            ports=[
                PortContract(name="clk", direction="input", width=1),
                PortContract(name="rst_n", direction="input", width=1),
                PortContract(name="valid_in", direction="input", width=1),
                PortContract(name="ready_out", direction="output", width=1),
            ],
            protocols=[
                ProtocolContract(
                    name="input_stream",
                    kind="ready_valid_stream",
                    recipe="ready_valid_backpressure",
                    request_signals=["valid_in"],
                    flow_control_signals=["ready_out"],
                    description="Input stream exposes ready/valid backpressure.",
                    metadata={"max_ratio": 1.0, "sample_cycles": 4},
                )
            ],
            performance_objective=PerformanceObjective(scenarios=[]),
        )


def test_architecture_planner_decomposes_mac_pipeline():
    arch = ArchitecturePlanner(SpecCompleter.complete(_mac_spec())).plan()

    assert arch.arch_type == "pipelined_datapath"
    assert len(arch.stages) == 3

    ops = [op for stage in arch.stages for op in stage.operation_specs]
    assert [op.kind for op in ops] == ["mul", "add"]
    assert ops[0].output == "tmp_0"
    assert ops[1].output == "y"
    assert any(reg.source == "tmp_0" for reg in arch.stages[0].registers)


def test_spec_ir_roundtrip_preserves_interfaces_and_assumptions():
    spec = SpecIR(
        name="StreamAdd",
        category="stream_pipeline",
        function=FunctionSpec(expr="out = data + 1"),
        ports=[
            PortSpec(name="data", direction="input", width=16),
            PortSpec(name="out", direction="output", width=16),
            PortSpec(name="in_valid", direction="input", width=1),
            PortSpec(name="in_ready", direction="output", width=1),
            PortSpec(name="out_valid", direction="output", width=1),
            PortSpec(name="out_ready", direction="input", width=1),
        ],
        interfaces=InterfaceSpec(input_protocol="ready_valid", output_protocol="ready_valid"),
        timing=TimingSpec(latency_max=2, latency_exact=2, throughput="1"),
        ppa=PPASpec(priority="timing_first", allow_pipeline=True, allow_clock_gating=True),
        verification=VerificationSpec(
            coverage_bins=["reset", "backpressure"],
            protocol_checks=["backpressure"],
            random_test_count=17,
        ),
        reset_type="async",
        reset_active="low",
        reset_name="rst_n",
    )

    restored = SpecIR.from_dict(spec.to_dict())

    assert restored.interfaces is not None
    assert restored.interfaces.input_protocol == "ready_valid"
    assert restored.timing.latency_exact == 2
    assert restored.verification.random_test_count == 17
    assert restored.reset_name == "rst_n"
    assert restored.reset_active == "low"
    assert restored.schema_version == IR_SCHEMA_VERSION


def test_core_ir_sidecars_carry_schema_version_and_read_legacy_dicts():
    behavior = SkillPPARunner._build_behavior_ir(
        GenerationContext(target=ModuleRequirement(name="LegacyDemo")),
        SpecIR(name="LegacyDemo"),
        None,
        None,
    )
    cycle = CycleIR(module_name="LegacyDemo")
    verification = VerificationPlanIR(module_name="LegacyDemo")

    assert behavior.to_dict()["schema_version"] == IR_SCHEMA_VERSION
    assert cycle.to_dict()["schema_version"] == IR_SCHEMA_VERSION
    assert verification.to_dict()["schema_version"] == IR_SCHEMA_VERSION
    assert CycleIR.from_dict({"module_name": "OldCycle"}).schema_version == IR_SCHEMA_VERSION
    assert VerificationPlanIR.from_dict({"module_name": "OldVerify"}).schema_version == IR_SCHEMA_VERSION


def test_perf_scenario_resolves_explicit_and_legacy_linked_checks():
    scenario = PerfScenario(
        name="compat",
        description="compatibility scenario",
        linked_checks=["explicit_check"],
        expected_observations={"linked_checks": ["legacy_check"], "ack": 1},
    )

    assert scenario.resolved_linked_checks() == ["explicit_check", "legacy_check"]
    assert scenario.expected_signal_names() == ["ack"]


def test_perf_scenario_timeline_overrides_base_stimulus():
    scenario = PerfScenario(
        name="timeline",
        description="timeline test",
        stimulus={"req": 0, "mode": 1},
        stimulus_timeline=[
            PerfStimulusStep(start_cycle=1, end_cycle=2, values={"req": 1}),
        ],
    )

    assert scenario.value_for_cycle("req", 0, 9) == 0
    assert scenario.value_for_cycle("req", 1, 9) == 1
    assert scenario.value_for_cycle("req", 2, 9) == 1
    assert scenario.value_for_cycle("req", 3, 9) == 0
    assert scenario.value_for_cycle("mode", 2, 9) == 1


def test_perf_scenario_recipe_drives_periodic_values():
    scenario = PerfScenario(
        name="recipe",
        description="recipe test",
        stimulus={"req": 0},
        stimulus_recipes=[
            PerfStimulusRecipe(
                kind="periodic",
                start_cycle=1,
                end_cycle=6,
                period=3,
                duty_cycles=2,
                values={"req": 1},
            )
        ],
    )

    observed = [scenario.value_for_cycle("req", cycle, 9) for cycle in range(8)]
    assert observed == [0, 1, 1, 0, 1, 1, 0, 0]


def test_transaction_ir_roundtrip_preserves_recipe_events():
    txn = TransactionIR(
        name="accepted_valid_to_done",
        trigger_signals=["valid_in"],
        completion_signals=["done"],
        recipe="single_outstanding_response",
        trigger_event="handshake",
        trigger_qualifiers=["ready_out"],
        completion_event="rise",
        sample_cycles=8,
        metadata={"max_outstanding": 1},
    )

    restored = TransactionIR.from_dict(txn.to_dict())

    assert restored.recipe == "single_outstanding_response"
    assert restored.trigger_event == "handshake"
    assert restored.trigger_qualifiers == ["ready_out"]
    assert restored.metadata["max_outstanding"] == 1


def test_transaction_recipe_registry_derives_single_outstanding_check():
    txn = TransactionContract(
        name="accepted_valid_to_done",
        trigger_signals=["valid_in"],
        completion_signals=["done"],
        recipe="single_outstanding_response",
        trigger_event="handshake",
        trigger_qualifiers=["ready_out"],
        completion_event="rise",
        sample_cycles=8,
        metadata={"max_outstanding": 1},
    )

    check = derive_transaction_perf_check(txn)

    assert "single_outstanding_response" in supported_transaction_recipes()
    assert check is not None
    assert check.name == "txn_accepted_valid_to_done_outstanding"
    assert check.kind == "completion_bound"
    assert check.source_event == "handshake"
    assert check.source_qualifiers == ["ready_out"]
    assert check.max_value == 1.0
    assert check.metadata["transaction_recipe"] == "single_outstanding_response"


def test_protocol_recipe_registry_derives_backpressure_check_and_scenario():
    proto = ProtocolContract(
        name="input_stream",
        kind="ready_valid_stream",
        recipe="ready_valid_backpressure",
        request_signals=["valid_in"],
        flow_control_signals=["ready_out"],
        metadata={"max_ratio": 0.75, "sample_cycles": 6},
    )

    check = derive_protocol_perf_check(proto)
    scenario = derive_protocol_scenario(proto)

    assert "ready_valid_backpressure" in supported_protocol_recipes()
    assert validate_protocol_recipe_contract(proto) == []
    assert check is not None
    assert check.name == "proto_input_stream_backpressure_ratio"
    assert check.kind == "stall_ratio"
    assert check.source_signals == ["valid_in"]
    assert check.sink_signals == ["ready_out"]
    assert check.max_ratio == 0.75
    assert check.metadata["protocol_recipe"] == "ready_valid_backpressure"
    assert scenario is not None
    assert scenario.linked_checks == ["proto_input_stream_backpressure_ratio"]
    assert scenario.stimulus == {"valid_in": 1, "ready_out": 1}
    assert scenario.expected_observations["protocol_recipe"] == "ready_valid_backpressure"


def test_protocol_recipe_registry_validates_required_fields():
    proto = ProtocolContract(
        name="input_stream",
        kind="ready_valid_stream",
        recipe="ready_valid_backpressure",
        request_signals=["valid_in"],
    )

    issues = validate_protocol_recipe_contract(proto)

    assert any("requires flow_control_signals" in issue for issue in issues)
    assert any("requires metadata max_ratio" in issue for issue in issues)


def test_transaction_recipe_registry_derives_default_scenario():
    txn = TransactionContract(
        name="accepted_valid_to_done",
        trigger_signals=["valid_in"],
        completion_signals=["done"],
        recipe="single_outstanding_response",
        trigger_event="handshake",
        trigger_qualifiers=["ready_out"],
        completion_event="rise",
        sample_cycles=8,
    )

    scenario = derive_transaction_scenario(txn)

    assert scenario is not None
    assert scenario.linked_transactions == ["accepted_valid_to_done"]
    assert scenario.stimulus == {"valid_in": 0, "ready_out": 1}
    assert scenario.stimulus_recipes[0].kind == "periodic"
    assert scenario.stimulus_recipes[0].values == {"valid_in": 1, "ready_out": 1}
    assert scenario.expected_observations["scenario_template"] == "periodic_issue"
    assert "single_outstanding_response" in scenario.tags
    assert "template:periodic_issue" in scenario.tags


def test_transaction_recipe_registry_validates_required_fields():
    latency_txn = TransactionContract(
        name="input_accept",
        trigger_signals=["valid_in"],
        completion_signals=["ready_out"],
        recipe="ready_valid_transfer",
    )
    outstanding_txn = TransactionContract(
        name="accepted_valid_to_done",
        trigger_signals=["valid_in"],
        completion_signals=["done"],
        recipe="single_outstanding_response",
        trigger_event="handshake",
    )

    latency_issues = validate_transaction_recipe_contract(latency_txn)
    outstanding_issues = validate_transaction_recipe_contract(outstanding_txn)

    assert latency_issues == [
        "transaction input_accept: recipe ready_valid_transfer requires max_cycles"
    ]
    assert any("requires metadata max_outstanding" in issue for issue in outstanding_issues)
    assert any("handshake trigger requires trigger_qualifiers" in issue for issue in outstanding_issues)


def test_transaction_recipe_registry_derives_latency_checks():
    ready_valid = TransactionContract(
        name="input_accept",
        trigger_signals=["valid_in"],
        completion_signals=["ready_out"],
        recipe="ready_valid_transfer",
        trigger_event="rise",
        completion_event="level",
        max_cycles=1,
    )
    request_grant = TransactionContract(
        name="request_to_grant",
        trigger_signals=["req"],
        completion_signals=["grant"],
        recipe="request_grant_completion",
        trigger_event="rise",
        completion_event="rise",
        max_cycles=3,
    )

    ready_check = derive_transaction_perf_check(ready_valid)
    grant_check = derive_transaction_perf_check(request_grant)

    assert ready_check is not None
    assert ready_check.name == "txn_input_accept_accept_latency"
    assert ready_check.kind == "latency"
    assert ready_check.max_cycles == 1
    assert grant_check is not None
    assert grant_check.name == "txn_request_to_grant_latency"
    assert grant_check.sink_event == "rise"
    assert grant_check.max_cycles == 3


def test_transaction_recipe_scenario_templates_accept_metadata_parameters():
    delayed = TransactionContract(
        name="delayed_req",
        trigger_signals=["req"],
        completion_signals=["done"],
        recipe="request_grant_completion",
        max_cycles=4,
        sample_cycles=6,
        metadata={"scenario_delay_cycles": 3},
    )
    backpressure = TransactionContract(
        name="stall_window",
        trigger_signals=["valid_in"],
        completion_signals=["stall"],
        recipe="backpressure_hold",
        sample_cycles=5,
        metadata={
            "max_ratio": 0.5,
            "backpressure_signal": "ready_in",
            "backpressure_start_cycle": 1,
            "backpressure_cycles": 3,
            "backpressure_value": 0,
        },
    )
    probe = TransactionContract(
        name="outstanding_probe",
        trigger_signals=["req"],
        completion_signals=["resp"],
        recipe="ordered_completion",
        sample_cycles=6,
        metadata={
            "max_outstanding": 1,
            "violation_probe": True,
            "violation_probe_pulses": 3,
        },
    )

    delayed_scenario = derive_transaction_scenario(delayed)
    backpressure_scenario = derive_transaction_scenario(backpressure)
    probe_scenario = derive_transaction_scenario(probe)

    assert delayed_scenario is not None
    assert delayed_scenario.expected_observations["scenario_delay_cycles"] == 3
    assert "delayed_completion" in delayed_scenario.tags
    assert delayed_scenario.stimulus_timeline[0].start_cycle == 3
    assert delayed_scenario.stimulus_timeline[0].values == {"done": 1}

    assert backpressure_scenario is not None
    assert backpressure_scenario.expected_observations["backpressure_signal"] == "ready_in"
    assert "backpressure_window" in backpressure_scenario.tags
    assert backpressure_scenario.stimulus_timeline[0].start_cycle == 1
    assert backpressure_scenario.stimulus_timeline[0].end_cycle == 3
    assert backpressure_scenario.stimulus_timeline[0].values == {"ready_in": 0}

    assert probe_scenario is not None
    assert probe_scenario.expected_observations["violation_probe"] is True
    assert "outstanding_violation_probe" in probe_scenario.tags
    assert [step.start_cycle for step in probe_scenario.stimulus_timeline] == [0, 1, 2]
    assert all(step.values == {"req": 1} for step in probe_scenario.stimulus_timeline)


def test_scenario_observation_context_reports_template_windows():
    txn = TransactionContract(
        name="stall_window",
        trigger_signals=["valid_in"],
        completion_signals=["stall"],
        recipe="backpressure_hold",
        sample_cycles=5,
        metadata={
            "max_ratio": 0.5,
            "backpressure_signal": "ready_in",
            "backpressure_start_cycle": 1,
            "backpressure_cycles": 3,
            "backpressure_value": 0,
        },
    )
    scenario = derive_transaction_scenario(txn)

    observed, expected = SkillPPARunner._scenario_observation_context(scenario, 5)

    assert expected["backpressure_signal"] == "ready_in"
    assert "backpressure_window" in expected["scenario_tags"]
    assert observed["scenario_timeline_steps"] == 1
    assert observed["scenario_timeline_signals"] == ["ready_in"]
    assert observed["backpressure_window_cycles"] == [1, 2, 3]
    assert observed["backpressure_values"] == [0, 0, 0]


def test_transaction_recipe_registry_derives_extended_protocol_checks():
    ordered = TransactionContract(
        name="ordered_resp",
        trigger_signals=["req"],
        completion_signals=["resp"],
        recipe="ordered_completion",
        allow_overlap=True,
        metadata={"max_outstanding": 2},
    )
    occupancy = TransactionContract(
        name="queue_bound",
        trigger_signals=["req"],
        completion_signals=["queue_depth"],
        recipe="bounded_queue_occupancy",
        sample_cycles=4,
        metadata={"min_value": 0, "max_value": 3},
    )
    backpressure = TransactionContract(
        name="stall_window",
        trigger_signals=["valid_in"],
        completion_signals=["stall"],
        recipe="backpressure_hold",
        sample_cycles=4,
        metadata={"max_ratio": 0.5},
    )

    ordered_check = derive_transaction_perf_check(ordered)
    occupancy_check = derive_transaction_perf_check(occupancy)
    backpressure_check = derive_transaction_perf_check(backpressure)
    occupancy_scenario = derive_transaction_scenario(occupancy)

    assert {"ordered_completion", "bounded_queue_occupancy", "backpressure_hold"} <= supported_transaction_recipes()
    assert ordered_check is not None
    assert ordered_check.kind == "completion_bound"
    assert ordered_check.max_value == 2.0
    assert occupancy_check is not None
    assert occupancy_check.kind == "occupancy"
    assert occupancy_check.max_value == 3.0
    assert backpressure_check is not None
    assert backpressure_check.kind == "stall_ratio"
    assert backpressure_check.max_ratio == 0.5
    assert occupancy_scenario is not None
    assert occupancy_scenario.stimulus == {"req": 1}
    assert occupancy_scenario.expected_observations["scenario_template"] == "hold_trigger"
    assert "sustained_window" in occupancy_scenario.tags


def test_cycle_transaction_ir_roundtrip_preserves_events():
    cycle_ir = CycleIR(
        module_name="HandshakeDemo",
        transactions=[
            CycleTransactionIR(
                name="accepted_valid_to_done",
                recipe="single_outstanding_response",
                trigger=TransactionEventIR(
                    name="accepted_valid_to_done_trigger",
                    event="handshake",
                    signals=["valid_in"],
                    qualifiers=["ready_out"],
                    condition="handshake(valid_in with ready_out)",
                ),
                completion=TransactionEventIR(
                    name="accepted_valid_to_done_completion",
                    event="rise",
                    signals=["done"],
                    condition="rise(done)",
                ),
                sample_cycles=8,
                temporal_relation="ordering=in_order; no_overlap; sample_window=8_cycles",
            )
        ],
    )

    restored = CycleIR.from_dict(cycle_ir.to_dict())

    assert restored.transactions[0].recipe == "single_outstanding_response"
    assert restored.transactions[0].trigger.event == "handshake"
    assert restored.transactions[0].trigger.qualifiers == ["ready_out"]
    assert restored.transactions[0].completion.condition == "rise(done)"
    assert restored.transactions[0].temporal_relation == "ordering=in_order; no_overlap; sample_window=8_cycles"


def test_dsl_generator_simulates_and_emits_verilog():
    completed = SpecCompleter.complete(_mac_spec())
    arch = ArchitecturePlanner(completed).plan()
    module = DSLGenerator(completed, arch).generate()

    sim = Simulator(module)
    sim.reset("rst")
    sim.set("a", 3)
    sim.set("b", 4)
    sim.set("c", 5)
    for _ in range(3):
        sim.step()

    assert sim.get_int("y") == 17
    assert module._generated_arch_ir["stages"][0]["operation_specs"][0]["kind"] == "mul"

    verilog = VerilogEmitter().emit(module)
    assert "module MacPipe" in verilog
    assert "tmp_0" in verilog


def test_dsl_generator_builds_hierarchical_wrapper_with_submodules():
    spec = SpecIR(
        name="HierPass",
        category="hierarchical",
        ports=[
            PortSpec(name="a", direction="input", width=8),
            PortSpec(name="y", direction="output", width=8),
        ],
    )
    arch = ArchitectureIR(
        arch_type="hierarchical",
        signal_widths={"a": 8, "y": 8},
        submodules=[
            SubmoduleInstanceSpec(
                module_type="pass_child",
                instance_name="u_pass",
                port_map={"in_data": "a", "out_data": "y"},
            )
        ],
        connections=[
            IRConnectionSpec(source="u_pass.out_data", sink="y", signal="y", width=8),
        ],
    )

    module = DSLGenerator(spec, arch).generate()
    sim = Simulator(module)
    sim.set("a", 23)
    sim.step()

    assert any(stmt.name == "u_pass" for stmt in module._top_level if hasattr(stmt, "name"))
    assert sim.get_int("y") == 23
    assert "u_pass" in VerilogEmitter().emit(module)


def test_architecture_planner_recognizes_hierarchical_category():
    spec = SpecIR(
        name="TopWrap",
        category="hierarchical",
        ports=[
            PortSpec(name="a", direction="input", width=8),
            PortSpec(name="y", direction="output", width=8),
        ],
    )

    arch = ArchitecturePlanner(spec).plan()

    assert arch.arch_type == "hierarchical"
    assert arch.output_names == ["y"]


def test_generate_dsl_skeleton_uses_public_dsl_generator():
    spec = BehavioralSpec(
        name="adder",
        inputs=[Input(8, "a"), Input(8, "b")],
        outputs=[Output(16, "y")],
        func=lambda inp: {"y": inp["a"] + inp["b"]},
    )

    module = generate_dsl_skeleton(spec, parent_name="Top")

    assert module.name == "Top_adder"
    assert set(module._inputs) == {"a", "b"}
    assert "y" in module._outputs


def test_agent_dsl_generator_uses_deterministic_generator_first():
    result = AgentDSLGenerator().generate(_mac_spec())

    assert result.used_deterministic_generator is True
    assert result.module is not None
    assert result.arch is not None
    assert result.module.name == "MacPipe"


def test_dsl_from_spec_fails_when_everything_falls_back(tmp_path):
    runner = SkillPPARunner("dummy")
    runner._skeleton_packages = {"mac0": _dummy_agent_package()}

    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "mac_spec.md").write_text("# markdown only\n")

    result = runner._run_dsl_from_spec(str(tmp_path))

    assert result.passed is False
    assert result.metrics["dsl_from_spec_success"] == 0
    assert result.metrics["dsl_from_spec_needs_generation"] == 1
    assert result.metrics["mac0_status"] == "needs_generation"


def test_dsl_from_spec_generates_from_structured_spec(tmp_path):
    runner = SkillPPARunner("dummy")
    pkg = _dummy_agent_package()
    runner._skeleton_packages = {"mac0": pkg}

    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "mac_spec.json").write_text(json.dumps(_mac_spec().to_dict()))

    result = runner._run_dsl_from_spec(str(tmp_path))

    assert result.passed is True
    assert result.metrics["dsl_from_spec_generated"] == 1
    assert result.metrics["dsl_from_spec_sim_passed"] == 1
    assert result.metrics["dsl_from_spec_lint_passed"] == 1
    assert result.metrics["mac0_source_status"] == "generated"
    assert result.metrics["mac0_status"] == "sim_passed"
    assert pkg.dsl_skeleton is not None


def test_review_spec_normalizes_ranged_port_names():
    gen_ctx = GenerationContext(
        target=ModuleRequirement(
            name="btb",
            pe_type="lookup",
            ports={
                "addrgen_btb_index[9:0]": {"dir": "input", "width": 64},
                "hit": {"dir": "output", "width": 1},
            },
        )
    )

    spec = SkillPPARunner._build_review_spec_from_context(gen_ctx)

    assert any(p.name == "addrgen_btb_index" and p.width == 10 for p in spec.ports)


def test_spec_gen_emits_machine_readable_sidecars(tmp_path):
    runner = SkillPPARunner("dummy")
    pkg = _dummy_agent_package()

    completed = SpecCompleter.complete(_mac_spec())
    arch = ArchitecturePlanner(completed).plan()
    pkg.dsl_skeleton = DSLGenerator(completed, arch).generate()
    pkg._behavior_requirement = {
        "interfaces": ["valid_ready_handshake:pipe"],
        "control_patterns": ["state_variables:pipe_valid"],
        "datapath_patterns": ["valid_gated_data"],
    }

    runner._skeleton_packages = {"mac0": pkg}
    runner._arch = ArchDefinition(name="DummyArch", processing_elements=[pkg.pe])

    result = runner._run_spec_gen(str(tmp_path))
    specs_dir = tmp_path / "specs"
    review_dir = tmp_path / "review"

    assert result.passed is True
    assert result.metrics["spec_genctx"] == 1
    assert result.metrics["spec_executable_ir"] == 1
    assert result.metrics["review_bundle_entries"] == 1
    assert result.metrics["spec_behavior_ir"] == 1
    assert result.metrics["spec_cycle_ir"] == 1
    assert result.metrics["spec_structural_ir"] == 1
    assert result.metrics["spec_verification_ir"] == 1
    assert (specs_dir / "mac_spec.md").exists()
    assert (specs_dir / "mac_genctx.json").exists()
    assert (specs_dir / "mac_review_spec.json").exists()
    assert (specs_dir / "mac_behaviorir.json").exists()
    assert (specs_dir / "mac_cycleir.json").exists()
    assert (specs_dir / "mac_structuralir.json").exists()
    assert (specs_dir / "mac_verificationir.json").exists()
    assert (specs_dir / "mac_specir.json").exists()
    assert (specs_dir / "mac_arch.json").exists()
    assert (specs_dir / "mac_bundle.json").exists()
    assert (review_dir / "01_spec_review.md").exists()
    assert (review_dir / "02_behavior_review.md").exists()
    assert (review_dir / "03_cycle_review.md").exists()
    assert (review_dir / "04_microarch_review.md").exists()
    assert (review_dir / "05_structure_review.md").exists()
    assert (review_dir / "06_verification_plan.md").exists()
    assert (review_dir / "07_lowering_report.md").exists()
    behavior_ir = json.loads((specs_dir / "mac_behaviorir.json").read_text())
    cycle_ir = json.loads((specs_dir / "mac_cycleir.json").read_text())
    structural_ir = json.loads((specs_dir / "mac_structuralir.json").read_text())
    verification_ir = json.loads((specs_dir / "mac_verificationir.json").read_text())
    assert behavior_ir["module_name"] == "MacPipe"
    assert behavior_ir["rules"][0]["effect"] == "y = a * b + c"
    assert any(state["name"] == "s1_tmp_0" for state in cycle_ir["states"])
    assert structural_ir["module_name"] == "MacPipe"
    assert verification_ir["scoreboards"][0]["implementation"] == "dsl.y"
    assert "Module: `MacPipe`" in (review_dir / "04_microarch_review.md").read_text()


def test_sidecar_projects_contract_transactions_to_behavior_and_verification_ir(tmp_path):
    mod = _PerfHandshakeDemo()
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    gen_ctx = GenerationContext(
        target=ModuleRequirement(
            name="PerfHandshakeDemo",
            pe_type="handshake_demo",
            ports={
                "clk": {"dir": "input", "width": 1},
                "rst_n": {"dir": "input", "width": 1},
                "valid_in": {"dir": "input", "width": 1},
                "ready_out": {"dir": "output", "width": 1},
                "done": {"dir": "output", "width": 1},
            },
        )
    )

    exported = SkillPPARunner._export_spec_sidecars(
        str(specs_dir),
        "handshake",
        gen_ctx,
        mod,
        None,
        ["u_handshake"],
    )

    behavior_ir = json.loads((specs_dir / "handshake_behaviorir.json").read_text())
    cycle_ir = json.loads((specs_dir / "handshake_cycleir.json").read_text())
    verification_ir = json.loads((specs_dir / "handshake_verificationir.json").read_text())
    bundle = json.loads((specs_dir / "handshake_bundle.json").read_text())

    assert exported["behavior_ir"] is True
    assert behavior_ir["transactions"][0]["name"] == "accepted_valid_to_done"
    assert behavior_ir["transactions"][0]["recipe"] == "single_outstanding_response"
    assert behavior_ir["rules"][-1]["category"] == "transaction"
    assert cycle_ir["transactions"][0]["name"] == "accepted_valid_to_done"
    assert cycle_ir["transactions"][0]["trigger"]["event"] == "handshake"
    assert cycle_ir["transactions"][0]["trigger"]["qualifiers"] == ["ready_out"]
    assert cycle_ir["transactions"][0]["completion"]["condition"] == "rise(done)"
    assert "sample_window=8_cycles" in cycle_ir["transactions"][0]["temporal_relation"]
    assert verification_ir["transactions"][0]["trigger_event"] == "handshake"
    assert any(
        tp["name"] == "txn_accepted_valid_to_done_trigger" and "ready_out" in tp["signals"]
        for tp in verification_ir["tracepoints"]
    )
    assert any(
        assertion["name"] == "txn_accepted_valid_to_done_recipe"
        for assertion in verification_ir["assertions"]
    )
    assert bundle["layer_alignment"]["behavior_to_verification"]["status"] == "passed"
    assert "behavior/cycle/verification" in bundle["layer_alignment"]["behavior_to_verification"]["detail"]


def test_dsl_from_spec_marks_needs_agent_when_only_review_sidecars_exist(tmp_path):
    runner = SkillPPARunner("dummy")
    runner._skeleton_packages = {"mac0": _dummy_agent_package()}

    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "mac_genctx.json").write_text("{}")
    (specs_dir / "mac_review_spec.json").write_text("{}")

    result = runner._run_dsl_from_spec(str(tmp_path))

    assert result.passed is False
    assert result.metrics["dsl_from_spec_needs_agent"] == 1
    assert result.metrics["mac0_status"] == "needs_agent"


def test_dsl_from_spec_runs_roundtrip_when_behavior_is_available(tmp_path):
    runner = SkillPPARunner("dummy")
    pkg = _adder_behavior_package()
    runner._skeleton_packages = {"adder0": pkg}

    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    spec = SpecIR(
        name="Adder",
        category="comb_alu",
        function=FunctionSpec(expr="y = a + b"),
        ports=[
            PortSpec(name="a", direction="input", width=8),
            PortSpec(name="b", direction="input", width=8),
            PortSpec(name="y", direction="output", width=9),
        ],
    )
    (specs_dir / "adder_spec.json").write_text(json.dumps(spec.to_dict()))

    result = runner._run_dsl_from_spec(str(tmp_path))
    lowering_report = (tmp_path / "review" / "07_lowering_report.md").read_text()

    assert result.passed is True
    assert result.metrics["dsl_from_spec_dsl_sim_passed"] == 1
    assert result.metrics["dsl_from_spec_roundtrip_passed"] == 1
    assert result.metrics["adder0_source_status"] == "generated"
    assert result.metrics["adder0_status"] == "roundtrip_passed"
    assert (tmp_path / "specs" / "adder_behaviorir.json").exists()
    assert (tmp_path / "specs" / "adder_cycleir.json").exists()
    assert (tmp_path / "specs" / "adder_structuralir.json").exists()
    assert (tmp_path / "specs" / "adder_verificationir.json").exists()
    assert "DSLSim" in lowering_report
    assert "roundtrip_passed" in lowering_report
    assert "spec_to_behavior: passed" in lowering_report
    assert "yes" in lowering_report


def test_dsl_sim_validator_and_verifier_accept_generated_hierarchy():
    spec = SpecIR(
        name="HierPass",
        category="hierarchical",
        ports=[
            PortSpec(name="a", direction="input", width=8),
            PortSpec(name="y", direction="output", width=8),
        ],
    )
    arch = ArchitectureIR(
        arch_type="hierarchical",
        signal_widths={"a": 8, "y": 8},
        submodules=[
            SubmoduleInstanceSpec(
                module_type="pass_child",
                instance_name="u_pass",
                port_map={"in_data": "a", "out_data": "y"},
            )
        ],
        connections=[
            IRConnectionSpec(source="u_pass.out_data", sink="y", signal="y", width=8),
        ],
    )
    module = DSLGenerator(spec, arch).generate()

    sim_result = DSLSimValidator(modules=[], use_xz=False).validate_module_instance(
        module,
        vectors=[{"a": 9}, {"a": 13}],
    )
    verifier_result = Verifier(enable_level_4=False).verify_module(
        module,
        VerilogEmitter().emit_design(module),
        golden_tests=[{"inputs": {"a": 9}, "expected_outputs": {"y": 9}}],
    )

    assert sim_result.simulation_ok is True
    assert verifier_result.passed is True
    assert verifier_result.level >= 3


def test_prompt_builder_supports_hierarchical_mode():
    gen_ctx = GenerationContext(
        target=ModuleRequirement(
            name="cluster",
            pe_type="cluster",
            ports={"done": {"dir": "output", "width": 1}},
        ),
        sub_modules=[SubModuleInfo(name="core0", submod_type="rv64_core", description="child core")],
    )
    gen_ctx.generation_task["hierarchy_mode"] = "hierarchical"

    prompt = build_generation_prompt(gen_ctx)

    assert "You MAY implement this design hierarchically." in prompt
    assert "Do NOT instantiate sub-modules as separate classes." not in prompt


def test_perf_verify_accepts_timeline_scenario():
    runner = SkillPPARunner("dummy")

    report = runner._run_perf_verify_module("PerfScenarioDemo", _PerfScenarioDemo())

    assert report.contract_present is True
    assert report.passed is True
    assert len(report.dynamic_checks) == 2
    assert all(check.passed for check in report.dynamic_checks)


def test_perf_verify_rejects_unknown_linked_check():
    runner = SkillPPARunner("dummy")
    mod = _PerfScenarioDemo()
    mod._module_contract.performance_objective.scenarios[0].linked_checks.append("missing_check")

    report = runner._run_perf_verify_module("PerfScenarioDemo", mod)

    assert report.passed is False
    assert any("unknown linked checks missing_check" in failure for failure in report.blocking_failures)
    assert report.failure_records[0]["kind"] == "schema"
    assert "missing_check" in report.failure_records[0]["message"]


def test_perf_verify_rejects_recipe_missing_required_metadata():
    runner = SkillPPARunner("dummy")
    mod = _PerfHandshakeDemo()
    mod._module_contract.transactions[0].metadata = {}

    report = runner._run_perf_verify_module("PerfHandshakeDemo", mod)

    assert report.passed is False
    assert any("requires metadata max_outstanding" in failure for failure in report.blocking_failures)
    assert report.failure_records[0]["kind"] == "schema"


def test_perf_verify_supports_richer_dynamic_check_kinds():
    runner = SkillPPARunner("dummy")

    report = runner._run_perf_verify_module("PerfRichChecksDemo", _PerfRichChecksDemo())

    assert report.contract_present is True
    assert report.passed is True
    names = {check.name: check for check in report.dynamic_checks}
    assert {"rich_occupancy", "rich_completion_bound", "rich_fairness"} <= set(names)
    assert names["rich_occupancy"].observed["peak_occupancy"] == 2.0
    assert names["rich_completion_bound"].observed["outstanding"] <= 1.0
    assert names["rich_fairness"].observed["fairness_ratio"] >= 0.5


def test_perf_verify_derives_protocol_recipe_checks():
    runner = SkillPPARunner("dummy")

    report = runner._run_perf_verify_module("PerfProtocolDemo", _PerfProtocolDemo())

    assert report.contract_present is True
    assert report.passed is True
    check = next(c for c in report.dynamic_checks if c.name == "proto_input_stream_backpressure_ratio")
    assert check.kind == "stall_ratio"
    assert check.expected["source"] == "VerificationPlanIR"
    assert check.expected["protocol_recipe"] == "ready_valid_backpressure"
    assert check.observed["scenario_cycles"] == 4
    assert check.passed is True


def test_perf_verify_supports_handshake_events_and_recipes():
    runner = SkillPPARunner("dummy")

    report = runner._run_perf_verify_module("PerfHandshakeDemo", _PerfHandshakeDemo())

    assert report.contract_present is True
    assert report.passed is True
    check = next(c for c in report.dynamic_checks if c.name == "txn_accepted_valid_to_done_outstanding")
    assert check.passed is True
    assert check.observed["peak_outstanding"] <= 1.0


def test_perf_verify_uses_auto_scenario_for_transaction_recipe():
    runner = SkillPPARunner("dummy")
    mod = _PerfHandshakeDemo()
    mod._module_contract.performance_objective.scenarios = []

    report = runner._run_perf_verify_module("PerfHandshakeDemo", mod)

    assert report.contract_present is True
    assert report.passed is True
    check = next(c for c in report.dynamic_checks if c.name == "txn_accepted_valid_to_done_outstanding")
    assert check.passed is True
    assert check.observed["peak_outstanding"] <= 1.0


def test_perf_verify_auto_scenario_drives_input_qualifiers():
    runner = SkillPPARunner("dummy")

    report = runner._run_perf_verify_module("PerfInputQualifierDemo", _PerfInputQualifierDemo())

    assert report.contract_present is True
    assert report.passed is True
    check = next(c for c in report.dynamic_checks if c.name == "txn_accepted_input_to_done_outstanding")
    assert check.passed is True
    assert check.observed["source_events"] > 0
    assert check.observed["peak_outstanding"] <= 1.0


def test_perf_verify_reports_auto_scenario_observation_context():
    runner = SkillPPARunner("dummy")
    mod = _PerfInputQualifierDemo()
    txn = mod._module_contract.transactions[0]
    txn.metadata.update(
        {
            "scenario_delay_cycles": 3,
            "violation_probe": True,
            "violation_probe_pulses": 2,
        }
    )

    report = runner._run_perf_verify_module("PerfInputQualifierDemo", mod)

    assert report.contract_present is True
    check = next(c for c in report.dynamic_checks if c.name == "txn_accepted_input_to_done_outstanding")
    assert check.expected["scenario_delay_cycles"] == 3
    assert check.expected["violation_probe"] is True
    assert "delayed_completion" in check.expected["scenario_tags"]
    assert "outstanding_violation_probe" in check.expected["scenario_tags"]
    assert check.observed["scenario_timeline_steps"] == 3
    assert check.observed["delayed_completion_cycle"] == 3
    assert check.observed["violation_probe_steps"] == 3
    assert check.observed["violation_probe_signal"] in {"done", "valid_in"}


def test_perf_verify_can_execute_transactions_from_verification_plan_ir():
    runner = SkillPPARunner("dummy")
    mod = _PerfHandshakeDemo()
    txn = mod._module_contract.transactions[0]
    mod._module_contract.transactions = []
    verification_ir = VerificationPlanIR(
        module_name="PerfHandshakeDemo",
        transactions=[
            TransactionIR(
                name=txn.name,
                trigger_signals=list(txn.trigger_signals),
                completion_signals=list(txn.completion_signals),
                recipe=txn.recipe,
                trigger_event=txn.trigger_event,
                trigger_qualifiers=list(txn.trigger_qualifiers),
                completion_event=txn.completion_event,
                sample_cycles=txn.sample_cycles,
                description=txn.description,
                metadata=dict(txn.metadata),
            )
        ],
    )

    report = runner._run_perf_verify_module("PerfHandshakeDemo", mod, verification_ir=verification_ir)

    assert report.contract_present is True
    assert report.passed is True
    check = next(c for c in report.dynamic_checks if c.name == "txn_accepted_valid_to_done_outstanding")
    assert check.expected["source"] == "VerificationPlanIR"
    assert check.passed is True


def test_verify_stage_loads_verification_plan_sidecar_for_perf_checks(tmp_path):
    runner = SkillPPARunner("dummy")
    mod = _PerfHandshakeDemo()
    txn = mod._module_contract.transactions[0]
    mod._module_contract.transactions = []
    runner._loaded = True
    runner._ppa_targets = [("PerfHandshakeDemo", lambda: mod)]

    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    verification_ir = VerificationPlanIR(
        module_name="PerfHandshakeDemo",
        transactions=[
            TransactionIR(
                name=txn.name,
                trigger_signals=list(txn.trigger_signals),
                completion_signals=list(txn.completion_signals),
                recipe=txn.recipe,
                trigger_event=txn.trigger_event,
                trigger_qualifiers=list(txn.trigger_qualifiers),
                completion_event=txn.completion_event,
                sample_cycles=txn.sample_cycles,
                description=txn.description,
                metadata=dict(txn.metadata),
            )
        ],
    )
    (specs_dir / "PerfHandshakeDemo_verificationir.json").write_text(
        json.dumps(verification_ir.to_dict())
    )

    result = runner._run_verify(str(tmp_path))
    report = json.loads((tmp_path / "verify" / "PerfHandshakeDemo.perf.json").read_text())

    assert result.passed is True
    assert result.metrics["verification_plan_sidecars_loaded"] == 1
    assert result.metrics["PerfHandshakeDemo_verification_plan"] == "PerfHandshakeDemo_verificationir.json"
    assert report["dynamic_checks"][0]["expected"]["source"] == "VerificationPlanIR"
    assert report["dynamic_checks"][0]["passed"] is True
