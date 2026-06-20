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
