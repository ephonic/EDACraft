"""Protocol VIP registry and unified helper kits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from rtlgen_x.verify.protocol_checkers import (
    check_ahblite_trace,
    check_apb_trace,
    check_axistream_trace,
    check_axilite_trace,
    check_reqrsp_trace,
    check_ready_valid_trace,
    check_wishbone_trace,
)
from rtlgen_x.verify.protocols import (
    AhbLiteTransfer,
    ApbTransfer,
    AxiLiteTransfer,
    AxiStreamTransfer,
    ReqRspTransfer,
    ReadyValidTransfer,
    WishboneTransfer,
    ahblite_reference_model,
    ahblite_sequence,
    apb_reference_model,
    apb_sequence,
    axilite_protocol_sequence,
    axilite_reference_model,
    axistream_reference_model,
    axistream_sequence,
    req_rsp_reference_model,
    req_rsp_sequence,
    ready_valid_reference_model,
    ready_valid_sequence,
    wishbone_clocked_protocol_sequence,
    wishbone_clocked_reference_model,
    wishbone_protocol_sequence,
    wishbone_reference_model,
)
from rtlgen_x.verify.python_uvm import PythonUvmSequenceItem
from rtlgen_x.verify.uvm import UvmSequenceStep


@dataclass(frozen=True)
class ProtocolVipKit:
    protocol: str
    transaction_type: Optional[type]
    sequence_builder: Callable[..., Any]
    reference_model_builder: Callable[..., object]
    checker: Callable[..., Any]
    notes: str = ""


def _normalize_protocol_name(name: str) -> str:
    normalized = str(name).strip().lower()
    aliases = {
        "readyvalid": "readyvalid",
        "ready_valid": "readyvalid",
        "axi4stream": "axi4stream",
        "axi_stream": "axi4stream",
        "axis": "axi4stream",
        "reqrsp": "reqrsp",
        "req_rsp": "reqrsp",
        "apb": "apb",
        "axilite": "axilite",
        "axi4lite": "axilite",
        "axi_lite": "axilite",
        "wishbone": "wishbone",
        "wishbone_clocked": "wishbone_clocked",
        "ahblite": "ahblite",
        "ahb_lite": "ahblite",
    }
    return aliases.get(normalized, normalized)


PROTOCOL_VIP_KITS: Dict[str, ProtocolVipKit] = {
    "readyvalid": ProtocolVipKit(
        protocol="ReadyValid",
        transaction_type=ReadyValidTransfer,
        sequence_builder=ready_valid_sequence,
        reference_model_builder=ready_valid_reference_model,
        checker=check_ready_valid_trace,
        notes="Scalar handshake channel with payload-stability checking.",
    ),
    "axi4stream": ProtocolVipKit(
        protocol="AXI4Stream",
        transaction_type=AxiStreamTransfer,
        sequence_builder=axistream_sequence,
        reference_model_builder=axistream_reference_model,
        checker=check_axistream_trace,
        notes="Streaming handshake channel with tlast/tkeep/tuser-aware checking.",
    ),
    "reqrsp": ProtocolVipKit(
        protocol="ReqRsp",
        transaction_type=ReqRspTransfer,
        sequence_builder=req_rsp_sequence,
        reference_model_builder=req_rsp_reference_model,
        checker=check_reqrsp_trace,
        notes="Minimal request/response channel with request and response stall checks.",
    ),
    "apb": ProtocolVipKit(
        protocol="APB",
        transaction_type=ApbTransfer,
        sequence_builder=apb_sequence,
        reference_model_builder=apb_reference_model,
        checker=check_apb_trace,
        notes="Two-phase APB control-plane helper path.",
    ),
    "axilite": ProtocolVipKit(
        protocol="AXI4Lite",
        transaction_type=AxiLiteTransfer,
        sequence_builder=axilite_protocol_sequence,
        reference_model_builder=axilite_reference_model,
        checker=check_axilite_trace,
        notes="Protocol-accurate AXI4-Lite helper path with channel-stability checking.",
    ),
    "wishbone": ProtocolVipKit(
        protocol="Wishbone",
        transaction_type=WishboneTransfer,
        sequence_builder=wishbone_protocol_sequence,
        reference_model_builder=wishbone_reference_model,
        checker=check_wishbone_trace,
        notes="Same-step Wishbone helper path.",
    ),
    "wishbone_clocked": ProtocolVipKit(
        protocol="WishboneClocked",
        transaction_type=WishboneTransfer,
        sequence_builder=wishbone_clocked_protocol_sequence,
        reference_model_builder=wishbone_clocked_reference_model,
        checker=check_wishbone_trace,
        notes="Registered-ack Wishbone helper path for clocked response timing.",
    ),
    "ahblite": ProtocolVipKit(
        protocol="AHBLite",
        transaction_type=AhbLiteTransfer,
        sequence_builder=ahblite_sequence,
        reference_model_builder=ahblite_reference_model,
        checker=check_ahblite_trace,
        notes="AHB-Lite single-outstanding helper path with wait-state stability checking.",
    ),
}


def get_protocol_vip_kit(protocol: str) -> ProtocolVipKit:
    key = _normalize_protocol_name(protocol)
    try:
        return PROTOCOL_VIP_KITS[key]
    except KeyError as exc:
        known = ", ".join(sorted(PROTOCOL_VIP_KITS))
        raise KeyError(f"unknown protocol VIP kit '{protocol}'. Known kits: {known}") from exc


def list_protocol_vip_kits() -> Mapping[str, ProtocolVipKit]:
    return dict(PROTOCOL_VIP_KITS)


def protocol_transfers_to_uvm_sequence_steps(
    protocol: str,
    transfers: Sequence[Any],
    *,
    sequence_kwargs: Optional[Mapping[str, Any]] = None,
) -> Tuple[UvmSequenceStep, ...]:
    kit = get_protocol_vip_kit(protocol)
    items = kit.sequence_builder(
        transfers,
        **dict(sequence_kwargs or {}),
    )
    steps = []
    for index, item in enumerate(items):
        if not isinstance(item, PythonUvmSequenceItem):
            raise TypeError(
                f"protocol kit '{kit.protocol}' returned unsupported sequence item type "
                f"{type(item)!r}; expected PythonUvmSequenceItem"
            )
        steps.append(
            UvmSequenceStep(
                inputs=dict(item.inputs),
                label=item.label or f"{_normalize_protocol_name(protocol)}_{index}",
            )
        )
    return tuple(steps)
