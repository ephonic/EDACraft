"""L3 ArchitectureIR tests for EarphoneFFT256."""

from earphone.modules.fft256.layer_L3_architecture.src.arch import ARCH


def test_architecture_contract_names_core_shape():
    assert ARCH.name == "EarphoneFFT256"
    assert ARCH.points == 256
    assert ARCH.sample_width == 16


def test_architecture_contract_contains_required_pipeline_and_invariants():
    assert {"input_stream", "fft_core", "output_stream"}.issubset(set(ARCH.stages))
    assert "sample per cycle" in ARCH.throughput.lower()
    assert len(ARCH.invariants) >= 3
