"""Protocol-oriented helpers for Python-side verification flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

from rtlgen_x.verify.python_uvm import PythonUvmSequenceItem


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
class AxiStreamTransfer:
    data: int
    last: int = 0
    keep: Optional[int] = None
    expected_ready: Optional[int] = None
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
                        self._storage[addr] = int(inputs.get("pwdata", 0))
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
    items = []
    base = dict(extra_inputs or {})
    for transfer in transfers:
        payload = {
            **base,
            data_name: int(transfer.data),
            valid_name: 1,
            last_name: int(transfer.last),
        }
        if keep_name is not None:
            payload[keep_name] = int(transfer.keep if transfer.keep is not None else 0)
        expected = None
        if transfer.expected_ready is not None:
            expected = {ready_name: int(transfer.expected_ready)}
        items.append(PythonUvmSequenceItem(inputs=payload, expected=expected, label=transfer.label))
        for _ in range(idle_cycles_between):
            idle = {
                **base,
                data_name: 0,
                valid_name: 0,
                last_name: 0,
            }
            if keep_name is not None:
                idle[keep_name] = 0
            items.append(
                PythonUvmSequenceItem(
                    inputs=idle,
                    label=f"{transfer.label}_idle" if transfer.label else None,
                )
            )
    return tuple(items)
