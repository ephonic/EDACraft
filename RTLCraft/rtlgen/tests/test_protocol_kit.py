from rtlgen.verify import (
    AhbLiteTransfer,
    ApbTransfer,
    AxiLiteTransfer,
    AxiStreamTransfer,
    ProtocolVipKit,
    ReadyValidTransfer,
    ReqRspTransfer,
    TraceSample,
    WishboneTransfer,
    get_protocol_vip_kit,
    list_protocol_vip_kits,
    protocol_transfers_to_uvm_sequence_steps,
)


def test_get_protocol_vip_kit_accepts_common_aliases():
    assert get_protocol_vip_kit("ready_valid").protocol == "ReadyValid"
    assert get_protocol_vip_kit("axis").protocol == "AXI4Stream"
    assert get_protocol_vip_kit("axi4lite").protocol == "AXI4Lite"
    assert get_protocol_vip_kit("wishbone_clocked").protocol == "WishboneClocked"
    assert get_protocol_vip_kit("ahb_lite").protocol == "AHBLite"


def test_list_protocol_vip_kits_exposes_expected_registry_entries():
    registry = list_protocol_vip_kits()

    assert "apb" in registry
    assert "axilite" in registry
    assert "axi4stream" in registry
    assert "wishbone" in registry
    assert "wishbone_clocked" in registry
    assert "readyvalid" in registry
    assert "reqrsp" in registry
    assert "ahblite" in registry
    assert all(isinstance(kit, ProtocolVipKit) for kit in registry.values())


def test_protocol_vip_kit_exposes_transaction_type_and_sequence_builder():
    assert get_protocol_vip_kit("readyvalid").transaction_type is ReadyValidTransfer
    assert get_protocol_vip_kit("reqrsp").transaction_type is ReqRspTransfer
    assert get_protocol_vip_kit("apb").transaction_type is ApbTransfer
    assert get_protocol_vip_kit("axilite").transaction_type is AxiLiteTransfer
    assert get_protocol_vip_kit("axi4stream").transaction_type is AxiStreamTransfer
    assert get_protocol_vip_kit("wishbone").transaction_type is WishboneTransfer
    assert get_protocol_vip_kit("wishbone_clocked").transaction_type is WishboneTransfer
    assert get_protocol_vip_kit("ahblite").transaction_type is AhbLiteTransfer

    seq = get_protocol_vip_kit("apb").sequence_builder(
        (ApbTransfer(addr=0x10, write=False, expected_rdata=0x55, label="rd0"),)
    )
    assert len(seq) == 2
    assert seq[0].inputs["psel"] == 1
    assert seq[1].expected == {"prdata": 0x55}


def test_protocol_vip_kit_reference_models_and_checkers_form_closed_loop():
    ready_kit = get_protocol_vip_kit("readyvalid")
    ready_model = ready_kit.reference_model_builder()
    assert ready_model.predict({"valid": 1, "data": 0x12}) == {"ready": 1}

    axis_kit = get_protocol_vip_kit("axis")
    axis_model = axis_kit.reference_model_builder()
    assert axis_model.predict({"tvalid": 1, "tdata": 0xAB}) == {"tready": 1}

    wb_kit = get_protocol_vip_kit("wishbone")
    wb_model = wb_kit.reference_model_builder(storage={4: 0x12345678})
    outputs = wb_model.predict(
        {"cyc_i": 1, "stb_i": 1, "we_i": 0, "adr_i": 16, "dat_i": 0, "sel_i": 0xF}
    )
    assert outputs["ack_o"] == 1
    assert outputs["dat_o"] == 0x12345678

    check = ready_kit.checker(
        (
            TraceSample(cycle=0, inputs={"data": 1, "valid": 1}, outputs={"ready": 0}, expected={}),
            TraceSample(cycle=1, inputs={"data": 2, "valid": 1}, outputs={"ready": 0}, expected={}),
        )
    )
    assert check.passed is False
    assert any(v.rule == "ready_valid_payload_stable" for v in check.violations)


def test_get_protocol_vip_kit_reports_known_names_on_error():
    try:
        get_protocol_vip_kit("no_such_protocol")
    except KeyError as exc:
        text = str(exc)
    else:
        raise AssertionError("expected KeyError for unknown protocol kit")

    assert "Known kits" in text
    assert "apb" in text
    assert "axi4stream" in text


def test_protocol_transfers_to_uvm_sequence_steps_bridges_protocol_sequences():
    apb_steps = protocol_transfers_to_uvm_sequence_steps(
        "apb",
        (ApbTransfer(addr=0x20, write=False, expected_rdata=0xCAFE, label="apb_rd"),),
    )
    assert len(apb_steps) == 2
    assert apb_steps[0].inputs["psel"] == 1
    assert apb_steps[0].inputs["penable"] == 0
    assert apb_steps[1].inputs["penable"] == 1
    assert apb_steps[0].label == "apb_rd"

    rv_steps = protocol_transfers_to_uvm_sequence_steps(
        "ready_valid",
        (ReadyValidTransfer(data=0x12, expected_ready=1, label="rv0"),),
    )
    assert len(rv_steps) == 1
    assert rv_steps[0].inputs["valid"] == 1
    assert rv_steps[0].inputs["data"] == 0x12

    wb_steps = protocol_transfers_to_uvm_sequence_steps(
        "wishbone_clocked",
        (WishboneTransfer(addr=4, write=True, wdata=0x55, label="wb_wr"),),
    )
    assert len(wb_steps) >= 2
    assert wb_steps[0].inputs["cyc_i"] == 1
    assert wb_steps[1].inputs["cyc_i"] == 1
