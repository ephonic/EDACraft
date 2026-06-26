"""L3 ArchitectureIR tests for EarphoneSIMD16."""

from earphone.modules.simd16.layer_L3_architecture.src.arch import ARCH


def test_architecture_contract_names_core_shape():
    assert ARCH.name == "EarphoneSIMD16"
    assert ARCH.vector_width == 256
    assert ARCH.lane_count == 16


def test_architecture_contract_contains_required_pipeline_and_invariants():
    assert {"issue", "int_execute", "fp_stage0", "fp_stage1", "fp_stage2", "writeback"}.issubset(set(ARCH.stages))
    assert ARCH.int_latency_cycles == 1
    assert ARCH.fp_latency_cycles == 3
