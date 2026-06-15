"""L3 ArchitectureIR tests for EarphoneQSPI."""

from earphone.modules.qspi.layer_L3_architecture.src.arch import ARCH


def test_architecture_contract_names_core_shape():
    assert ARCH.name == "EarphoneQSPI"
    assert ARCH.addr_width == 32
    assert ARCH.data_width == 32


def test_architecture_contract_contains_required_pipeline_and_invariants():
    assert {"idle", "cmd", "addr", "dummy", "data"}.issubset(set(ARCH.phases))
    assert ARCH.read_command == "0xEB"
    assert len(ARCH.invariants) >= 3
