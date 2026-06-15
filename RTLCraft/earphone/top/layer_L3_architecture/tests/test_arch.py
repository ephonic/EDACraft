"""Tests for the EarphoneTop L3 architecture contract."""

from earphone.top.layer_L3_architecture.src.arch import TOP_ARCH, describe


def test_top_architecture_lists_required_modules():
    modules = {module.module for module in TOP_ARCH.modules}
    assert {
        "EarphoneRV32",
        "EarphoneSIMD16",
        "EarphoneFFT256",
        "EarphoneQSPI",
        "EarphoneAPBBridge",
        "EarphoneSRAM256K",
        "EarphoneI2C",
    }.issubset(modules)


def test_top_architecture_apb_slot_contract_matches_bridge_decode():
    assert TOP_ARCH.apb_decode_field == "m_paddr[29:22]"
    assert TOP_ARCH.apb_slot_size_bytes == 4 * 1024 * 1024
    assert [slot.region for slot in TOP_ARCH.apb_slots] == [
        "QSPI",
        "SRAM",
        "SPI",
        "UART",
        "I2C",
        "I2S",
        "BTLE",
        "SIMD16",
    ]


def test_top_architecture_describe_is_machine_readable():
    info = describe()
    assert info["dsl_object_name"] == "earphone_top"
    assert info["verilog_module_name"] == "EarphoneTop"
    assert info["verilog_file_name"] == "earphone_top.v"
    assert "apb_debug" in info["external_interfaces"]
    assert "SRAM" in info["integrated_apb_regions"]
    assert "I2C" in info["integrated_apb_regions"]
    assert any("approval" in invariant for invariant in info["invariants"])
