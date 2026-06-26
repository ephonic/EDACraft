"""Protocol-oriented helpers for Python-side verification flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

from rtlgen.verify.python_uvm import PythonUvmSequenceItem


def _merge_write_lanes(prior: int, value: int, lane_mask: int, lane_count: int, lane_width: int = 8) -> int:
    merged = int(prior)
    for lane_idx in range(int(lane_count)):
        if ((int(lane_mask) >> lane_idx) & 1) == 0:
            continue
        shift = lane_idx * int(lane_width)
        mask = (1 << int(lane_width)) - 1
        merged &= ~(mask << shift)
        merged |= ((int(value) >> shift) & mask) << shift
    return int(merged)


@dataclass(frozen=True)
class ApbTransfer:
    addr: int
    write: bool
    wdata: int = 0
    strb: int = 0xF
    expected_rdata: Optional[int] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class AxiLiteTransfer:
    addr: int
    write: bool
    wdata: int = 0
    wstrb: int = 0xF
    expected_rdata: Optional[int] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class WishboneTransfer:
    addr: int
    write: bool
    wdata: int = 0
    sel: int = 0xF
    expected_rdata: Optional[int] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class AhbLiteTransfer:
    addr: int
    write: bool
    wdata: int = 0
    size: int = 2
    burst: int = 0
    prot: int = 0
    expected_rdata: Optional[int] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class AxiStreamTransfer:
    data: int
    last: int = 0
    keep: Optional[int] = None
    expected_ready: Optional[int] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class ReadyValidTransfer:
    data: int
    expected_ready: Optional[int] = None
    last: Optional[int] = None
    keep: Optional[int] = None
    user: Optional[int] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class ReqRspTransfer:
    req: int
    expected_req_ready: Optional[int] = None
    expected_rsp: Optional[int] = None
    addr: Optional[int] = None
    write: Optional[int] = None
    strb: Optional[int] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class Axi4Transfer:
    addr: int
    write: bool
    beats: Tuple[int, ...] = ()
    burst_len: Optional[int] = None
    size_bytes: int = 4
    burst_type: int = 1
    expected_rdata: Tuple[int, ...] = ()
    id_value: int = 0
    label: Optional[str] = None


@dataclass(frozen=True)
class CsrTransfer:
    addr: int
    write: bool
    wdata: int = 0
    expected_rdata: Optional[int] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class InterruptEvent:
    irq_mask: int
    cycles: int = 1
    expected_pending: Optional[int] = None
    label: Optional[str] = None


def ready_valid_sequence(
    transfers: Sequence[ReadyValidTransfer],
    *,
    data_name: str = "data",
    valid_name: str = "valid",
    ready_name: str = "ready",
    last_name: Optional[str] = None,
    keep_name: Optional[str] = None,
    user_name: Optional[str] = None,
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        payload = {
            **base,
            data_name: int(transfer.data),
            valid_name: 1,
        }
        if last_name is not None:
            payload[last_name] = int(transfer.last if transfer.last is not None else 0)
        if keep_name is not None:
            payload[keep_name] = int(transfer.keep if transfer.keep is not None else 0)
        if user_name is not None:
            payload[user_name] = int(transfer.user if transfer.user is not None else 0)
        expected = None
        if transfer.expected_ready is not None:
            expected = {ready_name: int(transfer.expected_ready)}
        items.append(PythonUvmSequenceItem(inputs=payload, expected=expected, label=transfer.label))
        for _ in range(idle_cycles_between):
            idle = {
                **base,
                data_name: 0,
                valid_name: 0,
            }
            if last_name is not None:
                idle[last_name] = 0
            if keep_name is not None:
                idle[keep_name] = 0
            if user_name is not None:
                idle[user_name] = 0
            items.append(
                PythonUvmSequenceItem(
                    inputs=idle,
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)


def ready_valid_reference_model(
    *,
    ready_output_name: str = "ready",
    ready_value: int = 1,
) -> object:
    class _ReadyValidReferenceModel:
        def reset(self) -> None:
            return None

        def predict(self, _inputs: Mapping[str, int]) -> Dict[str, int]:
            return {ready_output_name: int(ready_value)}

        def predict_batch(
            self,
            inputs_list: Sequence[Mapping[str, int]],
        ) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _ReadyValidReferenceModel()


def axistream_reference_model(
    *,
    ready_output_name: str = "tready",
    ready_value: int = 1,
) -> object:
    return ready_valid_reference_model(
        ready_output_name=ready_output_name,
        ready_value=ready_value,
    )


def req_rsp_sequence(
    transfers: Sequence[ReqRspTransfer],
    *,
    req_name: str = "req",
    req_valid_name: str = "req_valid",
    req_ready_name: str = "req_ready",
    rsp_name: str = "rsp",
    rsp_valid_name: str = "rsp_valid",
    rsp_ready_name: str = "rsp_ready",
    addr_name: Optional[str] = None,
    write_name: Optional[str] = None,
    strb_name: Optional[str] = None,
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        payload = {
            **base,
            req_name: int(transfer.req),
            req_valid_name: 1,
            rsp_ready_name: 1,
        }
        if addr_name is not None:
            payload[addr_name] = int(transfer.addr or 0)
        if write_name is not None:
            payload[write_name] = int(transfer.write or 0)
        if strb_name is not None:
            payload[strb_name] = int(transfer.strb or 0)
        expected = {}
        if transfer.expected_req_ready is not None:
            expected[req_ready_name] = int(transfer.expected_req_ready)
        if transfer.expected_rsp is not None:
            expected[rsp_name] = int(transfer.expected_rsp)
            expected[rsp_valid_name] = 1
        items.append(
            PythonUvmSequenceItem(
                inputs=payload,
                expected=expected or None,
                label=transfer.label,
            )
        )
        for _ in range(idle_cycles_between):
            idle = {
                **base,
                req_name: 0,
                req_valid_name: 0,
                rsp_ready_name: 1,
            }
            if addr_name is not None:
                idle[addr_name] = 0
            if write_name is not None:
                idle[write_name] = 0
            if strb_name is not None:
                idle[strb_name] = 0
            items.append(
                PythonUvmSequenceItem(
                    inputs=idle,
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)


def req_rsp_reference_model(
    *,
    response_map: Optional[Mapping[int, int]] = None,
    req_ready_name: str = "req_ready",
    rsp_name: str = "rsp",
    rsp_valid_name: str = "rsp_valid",
    req_name: str = "req",
) -> object:
    class _ReqRspReferenceModel:
        def __init__(self) -> None:
            self._responses = dict(response_map or {})

        def reset(self) -> None:
            return None

        def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
            outputs = {req_ready_name: 1, rsp_valid_name: 0, rsp_name: 0}
            if inputs.get("req_valid", inputs.get("valid", 0)):
                req = int(inputs.get(req_name, 0))
                if req in self._responses:
                    outputs[rsp_name] = int(self._responses[req])
                    outputs[rsp_valid_name] = 1
            return outputs

        def predict_batch(
            self,
            inputs_list: Sequence[Mapping[str, int]],
        ) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _ReqRspReferenceModel()


def apb_sequence(
    transfers: Sequence[ApbTransfer],
    *,
    addr_name: str = "paddr",
    wdata_name: str = "pwdata",
    write_name: str = "pwrite",
    select_name: str = "psel",
    enable_name: str = "penable",
    strb_name: str = "pstrb",
    expected_output_name: str = "prdata",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        setup = {
            **base,
            addr_name: int(transfer.addr),
            wdata_name: int(transfer.wdata),
            write_name: int(transfer.write),
            select_name: 1,
            enable_name: 0,
            strb_name: int(transfer.strb),
        }
        access = dict(setup)
        access[enable_name] = 1
        expected = (
            {expected_output_name: int(transfer.expected_rdata)}
            if (not transfer.write and transfer.expected_rdata is not None)
            else None
        )
        items.append(PythonUvmSequenceItem(inputs=setup, label=transfer.label))
        items.append(
            PythonUvmSequenceItem(
                inputs=access,
                expected=None if transfer.write else expected,
                label=transfer.label,
            )
        )
        for _ in range(idle_cycles_between):
            items.append(
                PythonUvmSequenceItem(
                    inputs={**base, select_name: 0, enable_name: 0, write_name: 0, strb_name: 0},
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)


def apb_reference_model(
    *,
    storage: Optional[Mapping[int, int]] = None,
    word_bytes: int = 4,
    read_output_name: str = "prdata",
) -> object:
    return register_reference_model(
        storage=storage,
        word_bytes=word_bytes,
        read_output_name=read_output_name,
    )


def axilite_sequence(
    transfers: Sequence[AxiLiteTransfer],
    *,
    addr_name: str = "awaddr",
    write_data_name: str = "wdata",
    write_strobe_name: str = "wstrb",
    write_valid_name: str = "write_valid",
    read_addr_name: str = "araddr",
    read_valid_name: str = "read_valid",
    expected_output_name: str = "rdata",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        if transfer.write:
            payload = {
                **base,
                addr_name: int(transfer.addr),
                write_data_name: int(transfer.wdata),
                write_strobe_name: int(transfer.wstrb),
                write_valid_name: 1,
                read_addr_name: 0,
                read_valid_name: 0,
            }
            items.append(PythonUvmSequenceItem(inputs=payload, label=transfer.label))
        else:
            payload = {
                **base,
                addr_name: 0,
                write_data_name: 0,
                write_strobe_name: 0,
                write_valid_name: 0,
                read_addr_name: int(transfer.addr),
                read_valid_name: 1,
            }
            expected = (
                {expected_output_name: int(transfer.expected_rdata)}
                if transfer.expected_rdata is not None
                else None
            )
            items.append(PythonUvmSequenceItem(inputs=payload, expected=expected, label=transfer.label))
        for _ in range(idle_cycles_between):
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        addr_name: 0,
                        write_data_name: 0,
                        write_strobe_name: 0,
                        write_valid_name: 0,
                        read_addr_name: 0,
                        read_valid_name: 0,
                    },
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)


def axilite_protocol_sequence(
    transfers: Sequence[AxiLiteTransfer],
    *,
    awaddr_name: str = "awaddr",
    awvalid_name: str = "awvalid",
    awprot_name: str = "awprot",
    wdata_name: str = "wdata",
    wstrb_name: str = "wstrb",
    wvalid_name: str = "wvalid",
    bvalid_name: str = "bvalid",
    bready_name: str = "bready",
    araddr_name: str = "araddr",
    arvalid_name: str = "arvalid",
    arprot_name: str = "arprot",
    rdata_name: str = "rdata",
    rvalid_name: str = "rvalid",
    rready_name: str = "rready",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        if transfer.write:
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        awaddr_name: int(transfer.addr),
                        awvalid_name: 1,
                        awprot_name: int(base.get(awprot_name, 0)),
                        wdata_name: int(transfer.wdata),
                        wstrb_name: int(transfer.wstrb),
                        wvalid_name: 1,
                        bready_name: 1,
                        araddr_name: 0,
                        arvalid_name: 0,
                        arprot_name: int(base.get(arprot_name, 0)),
                        rready_name: 0,
                    },
                    label=transfer.label,
                )
            )
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        awaddr_name: 0,
                        awvalid_name: 0,
                        awprot_name: int(base.get(awprot_name, 0)),
                        wdata_name: 0,
                        wstrb_name: 0,
                        wvalid_name: 0,
                        bready_name: 1,
                        araddr_name: 0,
                        arvalid_name: 0,
                        arprot_name: int(base.get(arprot_name, 0)),
                        rready_name: 0,
                    },
                    expected={bvalid_name: 1},
                    label=transfer.label,
                )
            )
        else:
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        awaddr_name: 0,
                        awvalid_name: 0,
                        awprot_name: int(base.get(awprot_name, 0)),
                        wdata_name: 0,
                        wstrb_name: 0,
                        wvalid_name: 0,
                        bready_name: 0,
                        araddr_name: int(transfer.addr),
                        arvalid_name: 1,
                        arprot_name: int(base.get(arprot_name, 0)),
                        rready_name: 1,
                    },
                    expected=None,
                    label=transfer.label,
                )
            )
            expected = {rvalid_name: 1}
            if transfer.expected_rdata is not None:
                expected[rdata_name] = int(transfer.expected_rdata)
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        awaddr_name: 0,
                        awvalid_name: 0,
                        awprot_name: int(base.get(awprot_name, 0)),
                        wdata_name: 0,
                        wstrb_name: 0,
                        wvalid_name: 0,
                        bready_name: 0,
                        araddr_name: 0,
                        arvalid_name: 0,
                        arprot_name: int(base.get(arprot_name, 0)),
                        rready_name: 1,
                    },
                    expected=expected,
                    label=transfer.label,
                )
            )
        for _ in range(idle_cycles_between):
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        awaddr_name: 0,
                        awvalid_name: 0,
                        awprot_name: int(base.get(awprot_name, 0)),
                        wdata_name: 0,
                        wstrb_name: 0,
                        wvalid_name: 0,
                        bready_name: 0,
                        araddr_name: 0,
                        arvalid_name: 0,
                        arprot_name: int(base.get(arprot_name, 0)),
                        rready_name: 0,
                    },
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)


def register_reference_model(
    *,
    storage: Optional[Mapping[int, int]] = None,
    word_bytes: int = 4,
    read_output_name: str = "prdata",
) -> object:
    class _RegisterReferenceModel:
        def __init__(self) -> None:
            self._initial = dict(storage or {})
            self._storage = dict(self._initial)
            self._last_read_data = 0

        def reset(self) -> None:
            self._storage = dict(self._initial)
            self._last_read_data = 0

        def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
            inputs = dict(inputs)
            current = {read_output_name: int(self._last_read_data)}
            if inputs.get("psel", 0):
                addr = int(inputs.get("paddr", 0)) // word_bytes
                if inputs.get("pwrite", 0):
                    if inputs.get("penable", 0):
                        lane_count = max(int(word_bytes), 1)
                        self._storage[addr] = _merge_write_lanes(
                            int(self._storage.get(addr, 0)),
                            int(inputs.get("pwdata", 0)),
                            int(inputs.get("pstrb", (1 << lane_count) - 1)),
                            lane_count,
                        )
                    return current
                if inputs.get("penable", 0):
                    self._last_read_data = int(self._storage.get(addr, 0))
                    return {read_output_name: int(self._last_read_data)}
                return current
            if inputs.get("write_valid", 0):
                addr = int(inputs.get("awaddr", 0)) // word_bytes
                self._storage[addr] = int(inputs.get("wdata", 0))
                return current
            if inputs.get("read_valid", 0):
                addr = int(inputs.get("araddr", 0)) // word_bytes
                self._last_read_data = int(self._storage.get(addr, 0))
                return {read_output_name: int(self._last_read_data)}
            return current

        def predict_batch(
            self,
            inputs_list: Sequence[Mapping[str, int]],
        ) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _RegisterReferenceModel()


def axilite_reference_model(
    *,
    storage: Optional[Mapping[int, int]] = None,
    word_bytes: int = 4,
    read_output_name: str = "rdata",
    read_valid_output_name: str = "rvalid",
    write_valid_output_name: str = "bvalid",
) -> object:
    class _AxiLiteReferenceModel:
        def __init__(self) -> None:
            self._initial = dict(storage or {})
            self._storage = dict(self._initial)
            self._pending_bvalid = False
            self._pending_rvalid = False
            self._pending_rdata = 0
            self._aw_seen = False
            self._aw_addr = 0
            self._w_seen = False
            self._w_data = 0
            self._w_strb = (1 << max(int(word_bytes), 1)) - 1

        def reset(self) -> None:
            self._storage = dict(self._initial)
            self._pending_bvalid = False
            self._pending_rvalid = False
            self._pending_rdata = 0
            self._aw_seen = False
            self._aw_addr = 0
            self._w_seen = False
            self._w_data = 0
            self._w_strb = (1 << max(int(word_bytes), 1)) - 1

        def _maybe_commit_write(self) -> None:
            if self._aw_seen and self._w_seen:
                lane_count = max(int(word_bytes), 1)
                self._storage[self._aw_addr] = _merge_write_lanes(
                    int(self._storage.get(self._aw_addr, 0)),
                    self._w_data,
                    self._w_strb,
                    lane_count,
                )
                self._pending_bvalid = True
                self._aw_seen = False
                self._w_seen = False

        def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
            outputs: Dict[str, int] = {}
            if self._pending_rvalid:
                outputs[read_valid_output_name] = 1
                outputs[read_output_name] = int(self._pending_rdata)
                self._pending_rvalid = False
            if self._pending_bvalid:
                outputs[write_valid_output_name] = 1
                self._pending_bvalid = False

            if inputs.get("awvalid", 0):
                self._aw_addr = int(inputs.get("awaddr", 0)) // word_bytes
                self._aw_seen = True
            if inputs.get("wvalid", 0):
                self._w_data = int(inputs.get("wdata", 0))
                self._w_strb = int(inputs.get("wstrb", (1 << max(int(word_bytes), 1)) - 1))
                self._w_seen = True
            self._maybe_commit_write()
            if inputs.get("arvalid", 0):
                addr = int(inputs.get("araddr", 0)) // word_bytes
                self._pending_rdata = int(self._storage.get(addr, 0))
                self._pending_rvalid = True
            return outputs

        def predict_batch(
            self,
            inputs_list: Sequence[Mapping[str, int]],
        ) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _AxiLiteReferenceModel()


def wishbone_reference_model(
    *,
    storage: Optional[Mapping[int, int]] = None,
    word_bytes: int = 4,
    read_output_name: str = "dat_o",
    ack_output_name: str = "ack_o",
    err_output_name: str = "err_o",
    retry_output_name: str = "rty_o",
) -> object:
    class _WishboneReferenceModel:
        def __init__(self) -> None:
            self._initial = dict(storage or {})
            self._storage = dict(self._initial)

        def reset(self) -> None:
            self._storage = dict(self._initial)

        def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
            outputs: Dict[str, int] = {
                read_output_name: 0,
                ack_output_name: 0,
                err_output_name: 0,
                retry_output_name: 0,
            }
            if not (inputs.get("cyc_i", 0) and inputs.get("stb_i", 0)):
                return outputs
            addr = int(inputs.get("adr_i", 0)) // word_bytes
            outputs[ack_output_name] = 1
            if inputs.get("we_i", 0):
                lane_count = max(int(word_bytes), 1)
                self._storage[addr] = _merge_write_lanes(
                    int(self._storage.get(addr, 0)),
                    int(inputs.get("dat_i", 0)),
                    int(inputs.get("sel_i", (1 << lane_count) - 1)),
                    lane_count,
                )
            else:
                outputs[read_output_name] = int(self._storage.get(addr, 0))
            return outputs

        def predict_batch(
            self,
            inputs_list: Sequence[Mapping[str, int]],
        ) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _WishboneReferenceModel()


def wishbone_clocked_reference_model(
    *,
    storage: Optional[Mapping[int, int]] = None,
    word_bytes: int = 4,
    read_output_name: str = "dat_o",
    ack_output_name: str = "ack_o",
    err_output_name: str = "err_o",
    retry_output_name: str = "rty_o",
) -> object:
    class _WishboneClockedReferenceModel:
        def __init__(self) -> None:
            self._initial = dict(storage or {})
            self._storage = dict(self._initial)
            self._pending_ack = False
            self._pending_read_valid = False
            self._pending_read_data = 0
            self._request_inflight = False

        def reset(self) -> None:
            self._storage = dict(self._initial)
            self._pending_ack = False
            self._pending_read_valid = False
            self._pending_read_data = 0
            self._request_inflight = False

        def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
            outputs: Dict[str, int] = {
                read_output_name: int(self._pending_read_data) if self._pending_read_valid else 0,
                ack_output_name: 1 if self._pending_ack else 0,
                err_output_name: 0,
                retry_output_name: 0,
            }

            self._pending_ack = False
            self._pending_read_valid = False
            self._pending_read_data = 0

            request = bool(inputs.get("cyc_i", 0) and inputs.get("stb_i", 0))
            if not request:
                self._request_inflight = False
                return outputs

            if self._request_inflight:
                return outputs

            self._request_inflight = True
            addr = int(inputs.get("adr_i", 0)) // word_bytes
            if inputs.get("we_i", 0):
                lane_count = max(int(word_bytes), 1)
                self._storage[addr] = _merge_write_lanes(
                    int(self._storage.get(addr, 0)),
                    int(inputs.get("dat_i", 0)),
                    int(inputs.get("sel_i", (1 << lane_count) - 1)),
                    lane_count,
                )
                self._pending_ack = True
            else:
                self._pending_read_data = int(self._storage.get(addr, 0))
                self._pending_read_valid = True
                self._pending_ack = True
            return outputs

        def predict_batch(
            self,
            inputs_list: Sequence[Mapping[str, int]],
        ) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _WishboneClockedReferenceModel()


def ahblite_reference_model(
    *,
    storage: Optional[Mapping[int, int]] = None,
    word_bytes: int = 4,
    read_output_name: str = "hrdata",
    ready_output_name: str = "hready",
    response_output_name: str = "hresp",
) -> object:
    class _AhbLiteReferenceModel:
        def __init__(self) -> None:
            self._initial = dict(storage or {})
            self._storage = dict(self._initial)

        def reset(self) -> None:
            self._storage = dict(self._initial)

        def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
            outputs: Dict[str, int] = {
                read_output_name: 0,
                ready_output_name: 1,
                response_output_name: 0,
            }
            if not inputs.get("hsel", 0):
                return outputs
            if int(inputs.get("htrans", 0)) not in (2, 3):
                return outputs
            addr = int(inputs.get("haddr", 0)) // word_bytes
            if inputs.get("hwrite", 0):
                self._storage[addr] = int(inputs.get("hwdata", 0))
            else:
                outputs[read_output_name] = int(self._storage.get(addr, 0))
            return outputs

        def predict_batch(
            self,
            inputs_list: Sequence[Mapping[str, int]],
        ) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _AhbLiteReferenceModel()


def csr_reference_model(
    *,
    storage: Optional[Mapping[int, int]] = None,
    read_output_name: str = "rdata",
) -> object:
    class _CsrReferenceModel:
        def __init__(self) -> None:
            self._initial = dict(storage or {})
            self._storage = dict(self._initial)

        def reset(self) -> None:
            self._storage = dict(self._initial)

        def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
            outputs = {read_output_name: 0}
            if inputs.get("csr_valid", 0):
                addr = int(inputs.get("csr_addr", 0))
                if inputs.get("csr_write", 0):
                    self._storage[addr] = int(inputs.get("csr_wdata", 0))
                else:
                    outputs[read_output_name] = int(self._storage.get(addr, 0))
            return outputs

        def predict_batch(self, inputs_list: Sequence[Mapping[str, int]]) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _CsrReferenceModel()


def interrupt_reference_model(
    *,
    initial_pending: int = 0,
    pending_output_name: str = "irq_pending",
) -> object:
    class _InterruptReferenceModel:
        def __init__(self) -> None:
            self._initial_pending = int(initial_pending)
            self._pending = self._initial_pending

        def reset(self) -> None:
            self._pending = self._initial_pending

        def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
            if inputs.get("irq_set", 0):
                self._pending |= int(inputs.get("irq_mask", 0))
            if inputs.get("irq_clear", 0):
                self._pending &= ~int(inputs.get("irq_mask", 0))
            return {pending_output_name: self._pending}

        def predict_batch(self, inputs_list: Sequence[Mapping[str, int]]) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _InterruptReferenceModel()


def axi_memory_reference_model(
    *,
    storage: Optional[Mapping[int, int]] = None,
    word_bytes: int = 4,
    read_data_name: str = "rdata",
) -> object:
    class _AxiMemoryReferenceModel:
        def __init__(self) -> None:
            self._initial = dict(storage or {})
            self._storage = dict(self._initial)
            self._read_queue = []
            self._write_addr = 0
            self._write_remaining = 0
            self._pending_bvalid = False

        def reset(self) -> None:
            self._storage = dict(self._initial)
            self._read_queue = []
            self._write_addr = 0
            self._write_remaining = 0
            self._pending_bvalid = False

        def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
            outputs = {"rvalid": 0, "rdata": 0, "rlast": 0, "bvalid": 0}
            if self._read_queue:
                outputs[read_data_name] = self._read_queue.pop(0)
                outputs["rdata"] = outputs[read_data_name]
                outputs["rvalid"] = 1
                outputs["rlast"] = 1 if not self._read_queue else 0
            if self._pending_bvalid:
                outputs["bvalid"] = 1
                self._pending_bvalid = False

            awvalid = int(inputs.get("awvalid", 0))
            wvalid = int(inputs.get("wvalid", 0))
            arvalid = int(inputs.get("arvalid", 0))
            if awvalid:
                self._write_addr = int(inputs.get("awaddr", 0)) // word_bytes
                self._write_remaining = int(inputs.get("awlen", 0)) + 1
            if wvalid:
                addr = self._write_addr
                self._storage[addr] = int(inputs.get("wdata", 0))
                self._write_addr = addr + 1
                if self._write_remaining > 0:
                    self._write_remaining -= 1
                if int(inputs.get("wlast", 0)) or self._write_remaining == 0:
                    self._pending_bvalid = True
            if arvalid:
                addr = int(inputs.get("araddr", 0)) // word_bytes
                length = int(inputs.get("arlen", 0)) + 1
                self._read_queue = [int(self._storage.get(addr + beat, 0)) for beat in range(length)]
            return outputs

        def predict_batch(
            self,
            inputs_list: Sequence[Mapping[str, int]],
        ) -> Tuple[Dict[str, int], ...]:
            return tuple(self.predict(inputs) for inputs in inputs_list)

    return _AxiMemoryReferenceModel()


def wishbone_sequence(
    transfers: Sequence[WishboneTransfer],
    *,
    addr_name: str = "wb_adr",
    wdata_name: str = "wb_dat_w",
    rdata_name: str = "wb_dat_r",
    write_name: str = "wb_we",
    cyc_name: str = "wb_cyc",
    stb_name: str = "wb_stb",
    sel_name: str = "wb_sel",
    ack_name: str = "wb_ack",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        access = {
            **base,
            addr_name: int(transfer.addr),
            wdata_name: int(transfer.wdata),
            write_name: int(transfer.write),
            cyc_name: 1,
            stb_name: 1,
            sel_name: int(transfer.sel),
        }
        expected = (
            {rdata_name: int(transfer.expected_rdata), ack_name: 1}
            if (not transfer.write and transfer.expected_rdata is not None)
            else {ack_name: 1}
        )
        items.append(PythonUvmSequenceItem(inputs=access, expected=expected, label=transfer.label))
        for _ in range(idle_cycles_between):
            items.append(
                PythonUvmSequenceItem(
                    inputs={**base, addr_name: 0, wdata_name: 0, write_name: 0, cyc_name: 0, stb_name: 0, sel_name: 0},
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)


def wishbone_protocol_sequence(
    transfers: Sequence[WishboneTransfer],
    *,
    addr_name: str = "adr_i",
    wdata_name: str = "dat_i",
    rdata_name: str = "dat_o",
    write_name: str = "we_i",
    cyc_name: str = "cyc_i",
    stb_name: str = "stb_i",
    sel_name: str = "sel_i",
    ack_name: str = "ack_o",
    err_name: str = "err_o",
    retry_name: str = "rty_o",
    cti_name: str = "cti_i",
    bte_name: str = "bte_i",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        expected = {
            ack_name: 1,
            err_name: 0,
            retry_name: 0,
        }
        if not transfer.write and transfer.expected_rdata is not None:
            expected[rdata_name] = int(transfer.expected_rdata)
        items.append(
            PythonUvmSequenceItem(
                inputs={
                    **base,
                    addr_name: int(transfer.addr),
                    wdata_name: int(transfer.wdata),
                    write_name: int(transfer.write),
                    cyc_name: 1,
                    stb_name: 1,
                    sel_name: int(transfer.sel),
                    cti_name: int(base.get(cti_name, 0)),
                    bte_name: int(base.get(bte_name, 0)),
                },
                expected=expected,
                label=transfer.label,
            )
        )
        for _ in range(idle_cycles_between):
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        addr_name: 0,
                        wdata_name: 0,
                        write_name: 0,
                        cyc_name: 0,
                        stb_name: 0,
                        sel_name: 0,
                        cti_name: int(base.get(cti_name, 0)),
                        bte_name: int(base.get(bte_name, 0)),
                    },
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)


def wishbone_clocked_protocol_sequence(
    transfers: Sequence[WishboneTransfer],
    *,
    addr_name: str = "adr_i",
    wdata_name: str = "dat_i",
    rdata_name: str = "dat_o",
    write_name: str = "we_i",
    cyc_name: str = "cyc_i",
    stb_name: str = "stb_i",
    sel_name: str = "sel_i",
    ack_name: str = "ack_o",
    err_name: str = "err_o",
    retry_name: str = "rty_o",
    cti_name: str = "cti_i",
    bte_name: str = "bte_i",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    idle = {
        **base,
        addr_name: 0,
        wdata_name: 0,
        write_name: 0,
        cyc_name: 0,
        stb_name: 0,
        sel_name: 0,
        cti_name: int(base.get(cti_name, 0)),
        bte_name: int(base.get(bte_name, 0)),
    }
    for transfer in transfers:
        items.append(
            PythonUvmSequenceItem(
                inputs={
                    **base,
                    addr_name: int(transfer.addr),
                    wdata_name: int(transfer.wdata),
                    write_name: int(transfer.write),
                    cyc_name: 1,
                    stb_name: 1,
                    sel_name: int(transfer.sel),
                    cti_name: int(base.get(cti_name, 0)),
                    bte_name: int(base.get(bte_name, 0)),
                },
                expected={
                    ack_name: 0,
                    err_name: 0,
                    retry_name: 0,
                    rdata_name: 0,
                },
                label=transfer.label,
            )
        )
        response_expected = {
            ack_name: 1,
            err_name: 0,
            retry_name: 0,
        }
        if transfer.write:
            response_expected[rdata_name] = 0
        elif transfer.expected_rdata is not None:
            response_expected[rdata_name] = int(transfer.expected_rdata)
        else:
            response_expected[rdata_name] = 0
        items.append(
            PythonUvmSequenceItem(
                inputs={
                    **base,
                    addr_name: int(transfer.addr),
                    wdata_name: int(transfer.wdata),
                    write_name: int(transfer.write),
                    cyc_name: 1,
                    stb_name: 1,
                    sel_name: int(transfer.sel),
                    cti_name: int(base.get(cti_name, 0)),
                    bte_name: int(base.get(bte_name, 0)),
                },
                expected=response_expected,
                label=transfer.label,
            )
        )
        for _ in range(idle_cycles_between):
            items.append(
                PythonUvmSequenceItem(
                    inputs=dict(idle),
                    expected={
                        ack_name: 0,
                        err_name: 0,
                        retry_name: 0,
                        rdata_name: 0,
                    },
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
        items.append(
            PythonUvmSequenceItem(
                inputs=dict(idle),
                expected={
                    ack_name: 0,
                    err_name: 0,
                    retry_name: 0,
                    rdata_name: 0,
                },
                label=f"{transfer.label}_gap" if transfer.label else None,
            )
        )
    return tuple(items)


def ahblite_sequence(
    transfers: Sequence[AhbLiteTransfer],
    *,
    addr_name: str = "haddr",
    wdata_name: str = "hwdata",
    rdata_name: str = "hrdata",
    write_name: str = "hwrite",
    trans_name: str = "htrans",
    size_name: str = "hsize",
    burst_name: str = "hburst",
    prot_name: str = "hprot",
    select_name: str = "hsel",
    ready_name: str = "hready",
    response_name: str = "hresp",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        expected = {
            ready_name: 1,
            response_name: 0,
        }
        if not transfer.write and transfer.expected_rdata is not None:
            expected[rdata_name] = int(transfer.expected_rdata)
        items.append(
            PythonUvmSequenceItem(
                inputs={
                    **base,
                    addr_name: int(transfer.addr),
                    wdata_name: int(transfer.wdata),
                    write_name: int(transfer.write),
                    trans_name: 2,
                    size_name: int(transfer.size),
                    burst_name: int(transfer.burst),
                    prot_name: int(transfer.prot),
                    select_name: 1,
                },
                expected=expected,
                label=transfer.label,
            )
        )
        for _ in range(idle_cycles_between):
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        addr_name: 0,
                        wdata_name: 0,
                        write_name: 0,
                        trans_name: 0,
                        size_name: 0,
                        burst_name: 0,
                        prot_name: 0,
                        select_name: 0,
                    },
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)


def axi4_sequence(
    transfers: Sequence[Axi4Transfer],
    *,
    awaddr_name: str = "awaddr",
    awvalid_name: str = "awvalid",
    awlen_name: str = "awlen",
    awsize_name: str = "awsize",
    awburst_name: str = "awburst",
    awid_name: str = "awid",
    wdata_name: str = "wdata",
    wvalid_name: str = "wvalid",
    wlast_name: str = "wlast",
    bid_name: str = "bid",
    bvalid_name: str = "bvalid",
    araddr_name: str = "araddr",
    arvalid_name: str = "arvalid",
    arlen_name: str = "arlen",
    arsize_name: str = "arsize",
    arburst_name: str = "arburst",
    arid_name: str = "arid",
    rdata_name: str = "rdata",
    rid_name: str = "rid",
    rvalid_name: str = "rvalid",
    rlast_name: str = "rlast",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        beats = tuple(int(beat) for beat in transfer.beats)
        burst_len = int(transfer.burst_len if transfer.burst_len is not None else max(len(beats), len(transfer.expected_rdata), 1))
        axsize = max(int(transfer.size_bytes).bit_length() - 1, 0)
        if transfer.write:
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        awaddr_name: int(transfer.addr),
                        awvalid_name: 1,
                        awlen_name: burst_len - 1,
                        awsize_name: axsize,
                        awburst_name: int(transfer.burst_type),
                        awid_name: int(transfer.id_value),
                        wdata_name: int(beats[0] if beats else 0),
                        wvalid_name: 1,
                        wlast_name: 1 if burst_len == 1 else 0,
                    },
                    label=transfer.label,
                )
            )
            for beat_idx in range(1, burst_len):
                items.append(
                    PythonUvmSequenceItem(
                        inputs={
                            **base,
                            awaddr_name: int(transfer.addr),
                            awvalid_name: 0,
                            awlen_name: burst_len - 1,
                            awsize_name: axsize,
                            awburst_name: int(transfer.burst_type),
                            awid_name: int(transfer.id_value),
                            wdata_name: int(beats[beat_idx] if beat_idx < len(beats) else 0),
                            wvalid_name: 1,
                            wlast_name: 1 if beat_idx == burst_len - 1 else 0,
                        },
                        label=transfer.label,
                    )
                )
            items.append(
                PythonUvmSequenceItem(
                    inputs={**base},
                    expected={bvalid_name: 1},
                    label=transfer.label,
                )
            )
        else:
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        araddr_name: int(transfer.addr),
                        arvalid_name: 1,
                        arlen_name: burst_len - 1,
                        arsize_name: axsize,
                        arburst_name: int(transfer.burst_type),
                        arid_name: int(transfer.id_value),
                    },
                    label=transfer.label,
                )
            )
            for beat_idx in range(burst_len):
                expected = {rvalid_name: 1, rlast_name: 1 if beat_idx == burst_len - 1 else 0}
                if beat_idx < len(transfer.expected_rdata):
                    expected[rdata_name] = int(transfer.expected_rdata[beat_idx])
                items.append(
                    PythonUvmSequenceItem(
                        inputs={**base},
                        expected=expected,
                        label=transfer.label,
                    )
                )
        for _ in range(idle_cycles_between):
            items.append(PythonUvmSequenceItem(inputs={**base}, label=f"{transfer.label}_idle" if transfer.label else None))
    return tuple(items)


def csr_sequence(
    transfers: Sequence[CsrTransfer],
    *,
    addr_name: str = "csr_addr",
    valid_name: str = "csr_valid",
    write_name: str = "csr_write",
    wdata_name: str = "csr_wdata",
    read_output_name: str = "rdata",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        expected = (
            {read_output_name: int(transfer.expected_rdata)}
            if (not transfer.write and transfer.expected_rdata is not None)
            else None
        )
        items.append(
            PythonUvmSequenceItem(
                inputs={
                    **base,
                    addr_name: int(transfer.addr),
                    valid_name: 1,
                    write_name: int(transfer.write),
                    wdata_name: int(transfer.wdata),
                },
                expected=expected,
                label=transfer.label,
            )
        )
        for _ in range(idle_cycles_between):
            items.append(
                PythonUvmSequenceItem(
                    inputs={**base, valid_name: 0, write_name: 0, wdata_name: 0, addr_name: 0},
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)


def interrupt_sequence(
    events: Sequence[InterruptEvent],
    *,
    set_name: str = "irq_set",
    clear_name: str = "irq_clear",
    mask_name: str = "irq_mask",
    pending_output_name: str = "irq_pending",
    clear_between: bool = False,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    items = []
    base = dict(extra_inputs or {})
    for event in events:
        for cycle in range(event.cycles):
            expected = (
                {pending_output_name: int(event.expected_pending)}
                if event.expected_pending is not None and cycle == event.cycles - 1
                else None
            )
            items.append(
                PythonUvmSequenceItem(
                    inputs={
                        **base,
                        set_name: 1 if cycle == 0 else 0,
                        clear_name: 0,
                        mask_name: int(event.irq_mask),
                    },
                    expected=expected,
                    label=event.label,
                )
            )
        if clear_between:
            items.append(
                PythonUvmSequenceItem(
                    inputs={**base, set_name: 0, clear_name: 1, mask_name: int(event.irq_mask)},
                    label=f"{event.label}_clear" if event.label else None,
                )
            )
    return tuple(items)


def axistream_sequence(
    transfers: Sequence[AxiStreamTransfer],
    *,
    data_name: str = "tdata",
    valid_name: str = "tvalid",
    ready_name: str = "tready",
    last_name: str = "tlast",
    keep_name: Optional[str] = "tkeep",
    idle_cycles_between: int = 0,
    extra_inputs: Optional[Mapping[str, int]] = None,
) -> Tuple[PythonUvmSequenceItem, ...]:
    return ready_valid_sequence(
        tuple(
            ReadyValidTransfer(
                data=int(transfer.data),
                expected_ready=transfer.expected_ready,
                last=int(transfer.last),
                keep=transfer.keep,
                label=transfer.label,
            )
            for transfer in transfers
        ),
        data_name=data_name,
        valid_name=valid_name,
        ready_name=ready_name,
        last_name=last_name,
        keep_name=keep_name,
        idle_cycles_between=idle_cycles_between,
        extra_inputs=extra_inputs,
    )
