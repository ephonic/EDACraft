"""L3 ArchitectureIR tests for EarphoneSRAM256K."""

from earphone.modules.sram256k.layer_L3_architecture.src.arch import ARCH


def test_architecture_contract_names_core_shape():
    assert ARCH.name == "EarphoneSRAM256K"
    assert ARCH.depth_words == 64 * 1024
    assert ARCH.data_width == 32


def test_architecture_contract_contains_required_pipeline_and_invariants():
    assert {"apb_request", "memory_access", "readback"}.issubset(set(ARCH.stages))
    assert ARCH.read_latency_cycles == 1
    assert ARCH.write_latency_cycles == 1
