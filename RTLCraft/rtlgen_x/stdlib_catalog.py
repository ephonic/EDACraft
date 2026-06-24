"""Public standard-library catalog for rtlgen_x.

This module is the executable source of truth for the current stdlib-facing
public entries that span:

1. DSL-side protocol bundles
2. DSL-side reusable components
3. verify-side protocol/VIP helper kits

The support levels here are intentionally conservative and are meant to align
with the documented support-matrix language used elsewhere in rtlgen_x.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Mapping, Optional, Tuple

StdlibKind = Literal["protocol", "component", "vip"]
StdlibStatus = Literal["stable", "partial", "experimental"]
StdlibSupportLevel = Literal["yes", "partial", "no"]

STDLIB_KINDS: Tuple[StdlibKind, ...] = ("protocol", "component", "vip")
STDLIB_STATUS_LEVELS: Tuple[StdlibStatus, ...] = ("stable", "partial", "experimental")
STDLIB_SUPPORT_LEVELS: Tuple[StdlibSupportLevel, ...] = ("yes", "partial", "no")


@dataclass(frozen=True)
class StdlibSupport:
    """Per-surface closure snapshot for one stdlib entry."""

    dsl_surface: StdlibSupportLevel
    lowering: StdlibSupportLevel
    python_sim: StdlibSupportLevel
    cpp_sim: StdlibSupportLevel
    emitted_rtl: StdlibSupportLevel
    readable_rtl: StdlibSupportLevel
    python_verify: StdlibSupportLevel
    sv_uvm: StdlibSupportLevel
    analysis: StdlibSupportLevel


@dataclass(frozen=True)
class StdlibEntry:
    """One public stdlib entry with support metadata."""

    name: str
    kind: StdlibKind
    family: str
    status: StdlibStatus
    summary: str
    support: StdlibSupport
    public_api: Tuple[str, ...]
    related: Tuple[str, ...] = ()
    notes: str = ""


def _support(
    *,
    dsl_surface: StdlibSupportLevel,
    lowering: StdlibSupportLevel,
    python_sim: StdlibSupportLevel,
    cpp_sim: StdlibSupportLevel,
    emitted_rtl: StdlibSupportLevel,
    readable_rtl: StdlibSupportLevel,
    python_verify: StdlibSupportLevel,
    sv_uvm: StdlibSupportLevel,
    analysis: StdlibSupportLevel,
) -> StdlibSupport:
    return StdlibSupport(
        dsl_surface=dsl_surface,
        lowering=lowering,
        python_sim=python_sim,
        cpp_sim=cpp_sim,
        emitted_rtl=emitted_rtl,
        readable_rtl=readable_rtl,
        python_verify=python_verify,
        sv_uvm=sv_uvm,
        analysis=analysis,
    )


_STDLIB_ENTRIES: Tuple[StdlibEntry, ...] = (
    StdlibEntry(
        name="ReadyValid",
        kind="protocol",
        family="channel",
        status="partial",
        summary="Canonical scalar ready/valid channel with matching verify helpers.",
        support=_support(
            dsl_surface="yes",
            lowering="partial",
            python_sim="partial",
            cpp_sim="partial",
            emitted_rtl="partial",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=(
            "rtlgen_x.dsl.ReadyValid",
            "rtlgen_x.verify.ready_valid_sequence",
            "rtlgen_x.verify.ready_valid_reference_model",
            "rtlgen_x.verify.check_ready_valid_trace",
        ),
        related=("ReadyValidRegister", "ReadyValidFIFO", "ReadyValidAsyncBridge", "ReadyValidVIP"),
        notes="Bundle authoring is available today, but full downstream semantic closure is still not uniform across every consumer.",
    ),
    StdlibEntry(
        name="ReqRsp",
        kind="protocol",
        family="channel",
        status="partial",
        summary="Minimal request/response channel with protocol-aware request/response grouping.",
        support=_support(
            dsl_surface="yes",
            lowering="partial",
            python_sim="partial",
            cpp_sim="partial",
            emitted_rtl="partial",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=(
            "rtlgen_x.dsl.ReqRsp",
            "rtlgen_x.verify.req_rsp_sequence",
            "rtlgen_x.verify.req_rsp_reference_model",
            "rtlgen_x.verify.check_reqrsp_trace",
        ),
        related=("ReqRspQueue", "ReqRspVIP"),
        notes="Useful for control-plane and transaction datapaths that do not need a full bus protocol.",
    ),
    StdlibEntry(
        name="APB",
        kind="protocol",
        family="control_bus",
        status="partial",
        summary="Low-complexity APB control-plane bundle with byte-enable-aware verification helpers.",
        support=_support(
            dsl_surface="yes",
            lowering="partial",
            python_sim="partial",
            cpp_sim="partial",
            emitted_rtl="partial",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=(
            "rtlgen_x.dsl.APB",
            "rtlgen_x.verify.apb_sequence",
            "rtlgen_x.verify.apb_reference_model",
            "rtlgen_x.verify.get_protocol_vip_kit('apb')",
        ),
        related=("APBRegisterBank", "APBVIP"),
        notes="Two-phase APB helper path is closed on the verify side; bundle-to-all-consumers closure is still conservative.",
    ),
    StdlibEntry(
        name="AXI4Lite",
        kind="protocol",
        family="control_bus",
        status="partial",
        summary="AXI4-Lite control-plane bundle with protocol-aware helper paths.",
        support=_support(
            dsl_surface="yes",
            lowering="partial",
            python_sim="partial",
            cpp_sim="partial",
            emitted_rtl="partial",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=(
            "rtlgen_x.dsl.AXI4Lite",
            "rtlgen_x.verify.axilite_protocol_sequence",
            "rtlgen_x.verify.axilite_reference_model",
            "rtlgen_x.verify.get_protocol_vip_kit('axilite')",
        ),
        related=("AXI4LiteRegisterBank", "AXI4LiteVIP"),
        notes="Registered response timing and byte-lane semantics are modeled in the verify path.",
    ),
    StdlibEntry(
        name="AXI4Stream",
        kind="protocol",
        family="stream",
        status="partial",
        summary="Streaming handshake bundle with tlast/tkeep/tuser-aware verification helpers.",
        support=_support(
            dsl_surface="yes",
            lowering="partial",
            python_sim="partial",
            cpp_sim="partial",
            emitted_rtl="partial",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=(
            "rtlgen_x.dsl.AXI4Stream",
            "rtlgen_x.verify.axistream_sequence",
            "rtlgen_x.verify.axistream_reference_model",
            "rtlgen_x.verify.get_protocol_vip_kit('axis')",
        ),
        related=("AXI4StreamVIP",),
        notes="Generated-UVM bridge is available for lightweight directed streaming stimulus.",
    ),
    StdlibEntry(
        name="Wishbone",
        kind="protocol",
        family="control_bus",
        status="partial",
        summary="Wishbone B4 bundle with simple and registered-ack verify helper modes.",
        support=_support(
            dsl_surface="yes",
            lowering="partial",
            python_sim="partial",
            cpp_sim="partial",
            emitted_rtl="partial",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=(
            "rtlgen_x.dsl.Wishbone",
            "rtlgen_x.verify.wishbone_protocol_sequence",
            "rtlgen_x.verify.wishbone_reference_model",
            "rtlgen_x.verify.get_protocol_vip_kit('wishbone')",
        ),
        related=("WishboneRegisterBank", "WishboneVIP", "WishboneClockedVIP"),
        notes="The verify path distinguishes same-step Wishbone from registered-ack WishboneClocked timing.",
    ),
    StdlibEntry(
        name="AHBLite",
        kind="protocol",
        family="control_bus",
        status="partial",
        summary="Single-outstanding AHB-Lite helper surface with wait-state stability checking.",
        support=_support(
            dsl_surface="yes",
            lowering="partial",
            python_sim="partial",
            cpp_sim="partial",
            emitted_rtl="partial",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=(
            "rtlgen_x.dsl.AHBLite",
            "rtlgen_x.verify.ahblite_sequence",
            "rtlgen_x.verify.ahblite_reference_model",
            "rtlgen_x.verify.get_protocol_vip_kit('ahb_lite')",
        ),
        related=("AHBLiteVIP",),
        notes="Protocol checking is available, but the full bundle story is still being standardized.",
    ),
    StdlibEntry(
        name="SkidBuffer",
        kind="component",
        family="buffer",
        status="partial",
        summary="One-entry elastic datapath buffer with empty-state bypass.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.SkidBuffer",),
        related=("ReadyValid",),
        notes="Good local closure today, but it is not yet part of a fully standardized generated-UVM component family.",
    ),
    StdlibEntry(
        name="ReadyValidRegister",
        kind="component",
        family="buffer",
        status="partial",
        summary="Single-stage registered ready/valid slice with backpressure handling.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.ReadyValidRegister",),
        related=("ReadyValid", "ReadyValidVIP"),
        notes="Regression-covered through lowering, simulation, emitted RTL, and Python-UVM; generated-UVM specialization remains lighter-weight.",
    ),
    StdlibEntry(
        name="ReadyValidFIFO",
        kind="component",
        family="buffer",
        status="partial",
        summary="Multi-beat ready/valid queue with occupancy tracking via level/count state.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.ReadyValidFIFO",),
        related=("ReadyValid", "ReadyValidVIP"),
        notes="Useful as the current protocol-aware queue primitive for ready/valid datapaths.",
    ),
    StdlibEntry(
        name="ReadyValidAsyncBridge",
        kind="component",
        family="cdc",
        status="partial",
        summary="Ready/valid async bridge built on explicit CDC-safe structure.",
        support=_support(
            dsl_surface="yes",
            lowering="partial",
            python_sim="partial",
            cpp_sim="partial",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="partial",
            sv_uvm="no",
            analysis="yes",
        ),
        public_api=("rtlgen_x.dsl.ReadyValidAsyncBridge",),
        related=("ReadyValid", "AsyncFIFO"),
        notes="CDC checker understands this primitive today; broader multi-clock verification closure remains explicitly partial.",
    ),
    StdlibEntry(
        name="ReqRspQueue",
        kind="component",
        family="queue",
        status="partial",
        summary="Lightweight request-path queue with direct response passthrough.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="yes",
            sv_uvm="partial",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.ReqRspQueue",),
        related=("ReqRsp", "ReqRspVIP"),
        notes="Useful for request-latency decoupling before a fuller protocol-aware queue family exists.",
    ),
    StdlibEntry(
        name="APBRegisterBank",
        kind="component",
        family="csr",
        status="partial",
        summary="Zero-wait-state APB register bank with byte-enable-backed storage updates.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="yes",
            sv_uvm="yes",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.APBRegisterBank", "rtlgen_x.verify.generate_uvm_runtime_bundle"),
        related=("APB", "APBVIP"),
        notes="This is the strongest current control-plane stdlib closure for lowering, simulation, and generated-UVM smoke usage; raw async reset release still appears as a CDC warning until a per-domain reset-release wrapper is authored.",
    ),
    StdlibEntry(
        name="AXI4LiteRegisterBank",
        kind="component",
        family="csr",
        status="partial",
        summary="Byte-enable-backed AXI4-Lite register bank with registered response behavior.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="yes",
            sv_uvm="yes",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.AXI4LiteRegisterBank", "rtlgen_x.verify.generate_uvm_runtime_bundle"),
        related=("AXI4Lite", "AXI4LiteVIP"),
        notes="Generated-UVM directed-sequence closure is available via protocol transfer bridging, and the current synchronous-reset implementation does not introduce a reset-release CDC warning.",
    ),
    StdlibEntry(
        name="WishboneRegisterBank",
        kind="component",
        family="csr",
        status="partial",
        summary="Byte-enable-backed registered-ack Wishbone slave for control-plane register storage.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="yes",
            sv_uvm="yes",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.WishboneRegisterBank", "rtlgen_x.verify.generate_uvm_runtime_bundle"),
        related=("Wishbone", "WishboneClockedVIP"),
        notes="Closes on the registered-ack Wishbone helper path rather than the simpler same-step mode, and the current synchronous-reset implementation does not introduce a reset-release CDC warning.",
    ),
    StdlibEntry(
        name="SyncFIFO",
        kind="component",
        family="queue",
        status="partial",
        summary="Synchronous FIFO authoring helper for single-clock storage buffering.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="partial",
            sv_uvm="no",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.SyncFIFO",),
        related=("AsyncFIFO",),
        notes="Executable/storage closure is decent, but protocol-aware verification and broader stdlib contracts are still lighter here.",
    ),
    StdlibEntry(
        name="AsyncFIFO",
        kind="component",
        family="cdc",
        status="partial",
        summary="Asynchronous FIFO primitive for explicit multi-clock crossings.",
        support=_support(
            dsl_surface="yes",
            lowering="partial",
            python_sim="partial",
            cpp_sim="partial",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="no",
            sv_uvm="no",
            analysis="yes",
        ),
        public_api=("rtlgen_x.dsl.AsyncFIFO",),
        related=("ReadyValidAsyncBridge",),
        notes="CDC analysis understands it as a safe primitive; full multi-clock behavioral closure is still intentionally conservative.",
    ),
    StdlibEntry(
        name="MAC",
        kind="component",
        family="arithmetic",
        status="partial",
        summary="Signed multiply-accumulate datapath helper with registered product and accumulator state.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="partial",
            sv_uvm="no",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.MAC",),
        related=("SignedMultiplier",),
        notes="Review-profile readability regression now covers this arithmetic helper; protocol-aware verify/UVM closure is still intentionally lightweight.",
    ),
    StdlibEntry(
        name="SignedMultiplier",
        kind="component",
        family="arithmetic",
        status="partial",
        summary="Configurable-latency signed multiplier with simple valid/ready shell.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="partial",
            sv_uvm="no",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.SignedMultiplier",),
        related=("MAC",),
        notes="Readable RTL regression covers the staged payload/valid structure, and PPA analysis can already point at multiplier-heavy hotspots for this style of datapath.",
    ),
    StdlibEntry(
        name="RegisterFile",
        kind="component",
        family="storage",
        status="partial",
        summary="Small explicit register-file helper with multiple read and write ports.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="partial",
            sv_uvm="no",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.RegisterFile",),
        related=("DualPortRAM",),
        notes="Review-profile readability regression covers explicit decoded reads and writes; memory semantic standardization beyond this helper remains future work.",
    ),
    StdlibEntry(
        name="DualPortRAM",
        kind="component",
        family="storage",
        status="partial",
        summary="Simple dual-port memory helper with one write/read port and one read port.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="partial",
            sv_uvm="no",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.DualPortRAM",),
        related=("RegisterFile", "LUT"),
        notes="Readable RTL regression covers storage declarations and simple dual-port access shape; broader macro-mapping policy is still analysis-first.",
    ),
    StdlibEntry(
        name="LUT",
        kind="component",
        family="storage",
        status="partial",
        summary="Combinational ROM-style lookup helper with initialized table contents.",
        support=_support(
            dsl_surface="yes",
            lowering="yes",
            python_sim="yes",
            cpp_sim="yes",
            emitted_rtl="yes",
            readable_rtl="yes",
            python_verify="partial",
            sv_uvm="no",
            analysis="partial",
        ),
        public_api=("rtlgen_x.dsl.LUT",),
        related=("DualPortRAM",),
        notes="Readable RTL regression covers initialization and combinational read shape; larger coefficient-table policies still belong in higher-level design review and PPA analysis.",
    ),
    StdlibEntry(
        name="ReadyValidVIP",
        kind="vip",
        family="channel",
        status="partial",
        summary="Python-VIP and checker surface for ready/valid traffic.",
        support=_support(
            dsl_surface="no",
            lowering="no",
            python_sim="no",
            cpp_sim="no",
            emitted_rtl="no",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="yes",
        ),
        public_api=(
            "rtlgen_x.verify.get_protocol_vip_kit('ready_valid')",
            "rtlgen_x.verify.protocol_transfers_to_uvm_sequence_steps",
        ),
        related=("ReadyValid", "ReadyValidRegister", "ReadyValidFIFO"),
        notes="Generated-UVM reuse is available for directed stimulus, while the richer closure remains on the Python-VIP/checker side.",
    ),
    StdlibEntry(
        name="ReqRspVIP",
        kind="vip",
        family="channel",
        status="partial",
        summary="Python-VIP helper kit for minimal request/response traffic.",
        support=_support(
            dsl_surface="no",
            lowering="no",
            python_sim="no",
            cpp_sim="no",
            emitted_rtl="no",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="yes",
        ),
        public_api=("rtlgen_x.verify.get_protocol_vip_kit('req_rsp')",),
        related=("ReqRsp", "ReqRspQueue"),
        notes="The transaction surface is useful today, but full generated-UVM standardization is still in progress.",
    ),
    StdlibEntry(
        name="APBVIP",
        kind="vip",
        family="control_bus",
        status="partial",
        summary="APB transaction/sequence/reference-model/checker kit.",
        support=_support(
            dsl_surface="no",
            lowering="no",
            python_sim="no",
            cpp_sim="no",
            emitted_rtl="no",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="yes",
            analysis="yes",
        ),
        public_api=(
            "rtlgen_x.verify.get_protocol_vip_kit('apb')",
            "rtlgen_x.verify.protocol_transfers_to_uvm_sequence_steps('apb', ...)",
        ),
        related=("APB", "APBRegisterBank"),
        notes="Local Python-VIP and generated-UVM directed smoke closure are both available for the current control-plane path.",
    ),
    StdlibEntry(
        name="AXI4LiteVIP",
        kind="vip",
        family="control_bus",
        status="partial",
        summary="AXI4-Lite transaction/sequence/reference-model/checker kit.",
        support=_support(
            dsl_surface="no",
            lowering="no",
            python_sim="no",
            cpp_sim="no",
            emitted_rtl="no",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="yes",
            analysis="yes",
        ),
        public_api=(
            "rtlgen_x.verify.get_protocol_vip_kit('axilite')",
            "rtlgen_x.verify.protocol_transfers_to_uvm_sequence_steps('axilite', ...)",
        ),
        related=("AXI4Lite", "AXI4LiteRegisterBank"),
        notes="Generated-UVM directed-sequence bridging is available for the current AXI4-Lite register-bank path.",
    ),
    StdlibEntry(
        name="AXI4StreamVIP",
        kind="vip",
        family="stream",
        status="partial",
        summary="AXI4-Stream transaction/sequence/reference-model/checker kit.",
        support=_support(
            dsl_surface="no",
            lowering="no",
            python_sim="no",
            cpp_sim="no",
            emitted_rtl="no",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="yes",
        ),
        public_api=(
            "rtlgen_x.verify.get_protocol_vip_kit('axis')",
            "rtlgen_x.verify.protocol_transfers_to_uvm_sequence_steps('axis', ...)",
        ),
        related=("AXI4Stream",),
        notes="Generated-UVM reuse currently targets lightweight directed streaming DUTs rather than a dedicated SV/UVM protocol environment.",
    ),
    StdlibEntry(
        name="WishboneVIP",
        kind="vip",
        family="control_bus",
        status="partial",
        summary="Wishbone same-step transaction/sequence/reference-model/checker kit.",
        support=_support(
            dsl_surface="no",
            lowering="no",
            python_sim="no",
            cpp_sim="no",
            emitted_rtl="no",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="yes",
        ),
        public_api=("rtlgen_x.verify.get_protocol_vip_kit('wishbone')",),
        related=("Wishbone", "WishboneRegisterBank", "WishboneClockedVIP"),
        notes="Same-step Wishbone is still distinct from the registered-ack WishboneClocked helper path.",
    ),
    StdlibEntry(
        name="WishboneClockedVIP",
        kind="vip",
        family="control_bus",
        status="partial",
        summary="Registered-ack Wishbone helper kit for clocked response timing.",
        support=_support(
            dsl_surface="no",
            lowering="no",
            python_sim="no",
            cpp_sim="no",
            emitted_rtl="no",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="yes",
            analysis="yes",
        ),
        public_api=(
            "rtlgen_x.verify.get_protocol_vip_kit('wishbone_clocked')",
            "rtlgen_x.verify.protocol_transfers_to_uvm_sequence_steps('wishbone_clocked', ...)",
        ),
        related=("Wishbone", "WishboneRegisterBank"),
        notes="This is the preferred VIP mode for the current Wishbone register-bank stdlib block.",
    ),
    StdlibEntry(
        name="AHBLiteVIP",
        kind="vip",
        family="control_bus",
        status="partial",
        summary="AHB-Lite helper kit with wait-state-aware checking.",
        support=_support(
            dsl_surface="no",
            lowering="no",
            python_sim="no",
            cpp_sim="no",
            emitted_rtl="no",
            readable_rtl="no",
            python_verify="yes",
            sv_uvm="partial",
            analysis="yes",
        ),
        public_api=("rtlgen_x.verify.get_protocol_vip_kit('ahb_lite')",),
        related=("AHBLite",),
        notes="Python-VIP and checking are available; fuller generated-UVM specialization remains future work.",
    ),
)


def _normalize_name(name: str) -> str:
    return "".join(ch for ch in str(name).strip().lower() if ch.isalnum())


_ENTRY_BY_KEY: Dict[str, StdlibEntry] = {}
for _entry in _STDLIB_ENTRIES:
    _ENTRY_BY_KEY[_normalize_name(_entry.name)] = _entry


STDLIB_CATALOG: Mapping[str, StdlibEntry] = dict(_ENTRY_BY_KEY)


def _normalize_kind(kind: Optional[str]) -> Optional[StdlibKind]:
    if kind is None:
        return None
    candidate = str(kind).strip().lower()
    if candidate not in STDLIB_KINDS:
        raise ValueError(f"unknown stdlib kind '{kind}'. Known kinds: {', '.join(STDLIB_KINDS)}")
    return candidate  # type: ignore[return-value]


def _normalize_status(status: Optional[str]) -> Optional[StdlibStatus]:
    if status is None:
        return None
    candidate = str(status).strip().lower()
    if candidate not in STDLIB_STATUS_LEVELS:
        raise ValueError(
            f"unknown stdlib status '{status}'. Known statuses: {', '.join(STDLIB_STATUS_LEVELS)}"
        )
    return candidate  # type: ignore[return-value]


def get_stdlib_entry(name: str) -> StdlibEntry:
    """Return one stdlib entry by canonical or loosely normalized name."""

    key = _normalize_name(name)
    try:
        return _ENTRY_BY_KEY[key]
    except KeyError as exc:
        known = ", ".join(entry.name for entry in _STDLIB_ENTRIES)
        raise KeyError(f"unknown stdlib entry '{name}'. Known entries: {known}") from exc


def list_stdlib_entries(
    *,
    kind: Optional[str] = None,
    status: Optional[str] = None,
) -> Mapping[str, StdlibEntry]:
    """Return the stdlib catalog filtered by kind and/or status."""

    normalized_kind = _normalize_kind(kind)
    normalized_status = _normalize_status(status)
    filtered = {}
    for entry in _STDLIB_ENTRIES:
        if normalized_kind is not None and entry.kind != normalized_kind:
            continue
        if normalized_status is not None and entry.status != normalized_status:
            continue
        filtered[entry.name] = entry
    return filtered


def emit_stdlib_support_matrix_markdown(
    *,
    kind: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """Render the current stdlib catalog as a Markdown support matrix."""

    normalized_kind = _normalize_kind(kind)
    normalized_status = _normalize_status(status)
    entries = [
        entry
        for entry in _STDLIB_ENTRIES
        if (normalized_kind is None or entry.kind == normalized_kind)
        and (normalized_status is None or entry.status == normalized_status)
    ]
    groups: Dict[str, list[StdlibEntry]] = {}
    for entry in entries:
        groups.setdefault(entry.kind, []).append(entry)

    lines = [
        "# rtlgen_x Stdlib Support Matrix",
        "",
        "This document snapshot is derived from the executable stdlib catalog in",
        "`rtlgen_x.stdlib_catalog`.",
        "",
        "Support levels are intentionally conservative:",
        "",
        "- `yes`: the surface is explicitly part of the current public closure",
        "- `partial`: the surface exists but still has important boundaries",
        "- `no`: not part of the current public story for that stdlib entry",
        "",
    ]
    for group_name in STDLIB_KINDS:
        group_entries = groups.get(group_name, [])
        if not group_entries:
            continue
        lines.extend(
            [
                f"## {group_name.title()} entries",
                "",
                "| Entry | Family | Status | DSL | Lowering | Python sim | C++ sim | Emitted RTL | Readable RTL | Python verify | SV/UVM | Analysis | Notes |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for entry in group_entries:
            support = entry.support
            lines.append(
                "| "
                f"`{entry.name}` | {entry.family} | `{entry.status}` | "
                f"{support.dsl_surface} | {support.lowering} | {support.python_sim} | "
                f"{support.cpp_sim} | {support.emitted_rtl} | {support.readable_rtl} | {support.python_verify} | "
                f"{support.sv_uvm} | {support.analysis} | {entry.notes} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "STDLIB_CATALOG",
    "STDLIB_KINDS",
    "STDLIB_STATUS_LEVELS",
    "STDLIB_SUPPORT_LEVELS",
    "StdlibEntry",
    "StdlibKind",
    "StdlibStatus",
    "StdlibSupport",
    "StdlibSupportLevel",
    "emit_stdlib_support_matrix_markdown",
    "get_stdlib_entry",
    "list_stdlib_entries",
]
