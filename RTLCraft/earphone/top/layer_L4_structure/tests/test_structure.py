"""Tests for the EarphoneTop L4 structure contract."""

from earphone.top.layer_L4_structure.src.structure import TOP_STRUCTURE, describe


def test_top_structure_contains_required_subblocks():
    names = {subblock.instance for subblock in TOP_STRUCTURE.subblocks}
    assert {"cpu", "simd16", "fft256", "qspi", "apb_bridge", "sram", "i2c"}.issubset(names)


def test_top_structure_subblocks_have_interfaces():
    for subblock in TOP_STRUCTURE.subblocks:
        assert subblock.module.startswith("Earphone")
        assert subblock.interfaces


def test_top_structure_connections_cover_integrated_apb_slaves():
    connections = {f"{conn.source}->{conn.sink}" for conn in TOP_STRUCTURE.connections}
    assert "apb_bridge.slot1->sram" in connections
    assert "apb_bridge.slot4->i2c" in connections
    info = describe()
    assert "qspi_pads" in info["external_interfaces"]
    assert "i2c_pads" in info["external_interfaces"]
