"""
rtlgen.netlist — Structural Verilog netlist parser.

Parses ABC-style mapped Verilog into a cell/instance graph for timing analysis
and gate sizing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class NetlistPin:
    name: str
    net_name: str


@dataclass
class NetlistCell:
    name: str  # instance name
    cell_type: str
    pins: Dict[str, NetlistPin] = field(default_factory=dict)


@dataclass
class NetlistNet:
    name: str
    driver: Optional[Tuple[str, str]] = None  # (cell_name, pin_name)
    loads: List[Tuple[str, str]] = field(default_factory=list)  # (cell_name, pin_name)
    is_port: bool = False
    port_direction: Optional[str] = None


@dataclass
class Netlist:
    module_name: str
    ports: Dict[str, Dict[str, str]] = field(default_factory=dict)
    nets: Dict[str, NetlistNet] = field(default_factory=dict)
    cells: Dict[str, NetlistCell] = field(default_factory=dict)


def parse_mapped_verilog(text: str) -> Netlist:
    """Parse ABC-style mapped Verilog into a Netlist object."""
    lines = text.splitlines()
    module_name = None
    nets: Dict[str, NetlistNet] = {}
    cells: Dict[str, NetlistCell] = {}
    ports: Dict[str, Dict[str, str]] = {}

    # Concatenate lines that are broken by backslashes
    cleaned_lines: List[str] = []
    buf = ""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if line.endswith("\\"):
            buf += line[:-1]
        else:
            cleaned_lines.append(buf + line)
            buf = ""
    if buf:
        cleaned_lines.append(buf)

    in_module = False
    for line in cleaned_lines:
        # module declaration
        m = re.match(r"module\s+(\w+)\s*\(", line)
        if m:
            module_name = m.group(1)
            in_module = True
            continue
        if line.startswith("endmodule"):
            in_module = False
            continue
        if not in_module:
            continue

        # input / output / wire
        if line.startswith("input ") or line.startswith("output ") or line.startswith("wire "):
            decl = line.rstrip(";").strip()
            kind, rest = decl.split(None, 1)
            # split by commas
            names = [n.strip() for n in rest.split(",") if n.strip()]
            for name in names:
                if name not in nets:
                    nets[name] = NetlistNet(name=name)
                if kind in ("input", "output"):
                    nets[name].is_port = True
                    nets[name].port_direction = kind
                    ports[name] = {"direction": kind}
            continue

        # cell instantiation: CELL_TYPE inst_name (.PIN(net), ...);
        m = re.match(r"(\w+)\s+(\w+)\s*\(", line)
        if m:
            cell_type = m.group(1)
            inst_name = m.group(2)
            # extract pin mappings
            inner = line[line.find("(") + 1:line.rfind(")")]
            pin_map = {}
            # split by commas, but be careful with nested parens (not expected here)
            for part in inner.split(","):
                part = part.strip()
                pm = re.match(r"\.(\w+)\s*\(\s*(.*?)\s*\)", part)
                if pm:
                    pin_name = pm.group(1)
                    net_name = pm.group(2)
                    pin_map[pin_name] = NetlistPin(name=pin_name, net_name=net_name)
                    if net_name not in nets:
                        nets[net_name] = NetlistNet(name=net_name)
            cell = NetlistCell(name=inst_name, cell_type=cell_type, pins=pin_map)
            cells[inst_name] = cell

            # Update net connectivity
            for pin_name, pin in pin_map.items():
                # We don't know direction yet; we'll infer later from library
                # For now just record loads, and any pin could be driver.
                nets[pin.net_name].loads.append((inst_name, pin_name))
            continue

    if module_name is None:
        raise ValueError("No module declaration found in Verilog")

    # Second pass: try to infer drivers using a heuristic:
    # For nets connected to ports, input ports drive the net; output ports are driven.
    # For internal nets, if only one cell pin is connected and the rest are ports/cells,
    # we still can't tell.  We'll leave driver inference to the timing engine which has
    # the Liberty library.
    netlist = Netlist(module_name=module_name, ports=ports, nets=nets, cells=cells)
    return netlist


def parse_mapped_blif(text: str) -> Netlist:
    """Parse ABC-style mapped BLIF into a Netlist object.

    Supports .subckt (technology-mapped gates) and .latch (sequential elements).
    """
    lines = text.splitlines()
    module_name = None
    nets: Dict[str, NetlistNet] = {}
    cells: Dict[str, NetlistCell] = {}
    ports: Dict[str, Dict[str, str]] = {}

    # Concatenate backslash-continued lines
    cleaned_lines: List[str] = []
    buf = ""
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.endswith("\\"):
            buf += s[:-1] + " "
        else:
            cleaned_lines.append(buf + s)
            buf = ""
    if buf:
        cleaned_lines.append(buf)

    subckt_counter = 0
    latch_counter = 0

    # Ensure constant nets exist
    for const in ("gnd", "vdd", "0", "1"):
        nets[const] = NetlistNet(name=const)

    for line in cleaned_lines:
        if line.startswith(".model "):
            parts = line.split()
            module_name = parts[1] if len(parts) > 1 else "top"
            continue
        if line.startswith(".inputs "):
            names = line[7:].strip().split()
            for name in names:
                if name not in nets:
                    nets[name] = NetlistNet(name=name)
                nets[name].is_port = True
                nets[name].port_direction = "input"
                ports[name] = {"direction": "input"}
            continue
        if line.startswith(".outputs "):
            names = line[8:].strip().split()
            for name in names:
                if name not in nets:
                    nets[name] = NetlistNet(name=name)
                nets[name].is_port = True
                nets[name].port_direction = "output"
                ports[name] = {"direction": "output"}
            continue
        if line.startswith(".subckt "):
            parts = line[7:].strip().split()
            if not parts:
                continue
            cell_type = parts[0]
            pin_map: Dict[str, NetlistPin] = {}
            for part in parts[1:]:
                if "=" in part:
                    pin_name, net_name = part.split("=", 1)
                    pin_map[pin_name] = NetlistPin(name=pin_name, net_name=net_name)
                    if net_name not in nets:
                        nets[net_name] = NetlistNet(name=net_name)
            inst_name = f"u{subckt_counter}_{cell_type}"
            subckt_counter += 1
            cell = NetlistCell(name=inst_name, cell_type=cell_type, pins=pin_map)
            cells[inst_name] = cell
            for pin_name, pin in pin_map.items():
                nets[pin.net_name].loads.append((inst_name, pin_name))
            continue
        if line.startswith(".names "):
            parts = line[6:].strip().split()
            if len(parts) >= 1:
                output_net = parts[-1]
                input_nets = parts[:-1]
                for n in input_nets + [output_net]:
                    if n not in nets:
                        nets[n] = NetlistNet(name=n)
                n_inputs = len(input_nets)
                if n_inputs == 0:
                    # constant driver (e.g., gnd/vdd) — treat as small buffer
                    cell_type = "INVX1"
                    pin_map = {"A": NetlistPin(name="A", net_name="gnd"), "Y": NetlistPin(name="Y", net_name=output_net)}
                elif n_inputs == 1:
                    cell_type = "INVX1"
                    pin_map = {"A": NetlistPin(name="A", net_name=input_nets[0]), "Y": NetlistPin(name="Y", net_name=output_net)}
                elif n_inputs == 2:
                    cell_type = "NAND2X1"
                    pin_map = {
                        "A": NetlistPin(name="A", net_name=input_nets[0]),
                        "B": NetlistPin(name="B", net_name=input_nets[1]),
                        "Y": NetlistPin(name="Y", net_name=output_net),
                    }
                else:
                    cell_type = "NAND3X1"
                    pin_map = {
                        "A": NetlistPin(name="A", net_name=input_nets[0]),
                        "B": NetlistPin(name="B", net_name=input_nets[1]),
                        "C": NetlistPin(name="C", net_name=input_nets[2]),
                        "Y": NetlistPin(name="Y", net_name=output_net),
                    }
                inst_name = f"g{subckt_counter}"
                subckt_counter += 1
                cell = NetlistCell(name=inst_name, cell_type=cell_type, pins=pin_map)
                cells[inst_name] = cell
                for pin_name, pin in pin_map.items():
                    if pin_name != "Y":
                        nets[pin.net_name].loads.append((inst_name, pin_name))
                    else:
                        nets[pin.net_name].loads.append((inst_name, pin_name))
                        nets[pin.net_name].driver = (inst_name, pin_name)
            continue
        if line.startswith(".latch "):
            parts = line[6:].strip().split()
            if len(parts) >= 2:
                input_net = parts[0]
                output_net = parts[1]
                for n in (input_net, output_net):
                    if n not in nets:
                        nets[n] = NetlistNet(name=n)
                inst_name = f"latch{latch_counter}"
                latch_counter += 1
                pin_map = {
                    "D": NetlistPin(name="D", net_name=input_net),
                    "Q": NetlistPin(name="Q", net_name=output_net),
                }
                cell = NetlistCell(name=inst_name, cell_type="LATCH", pins=pin_map)
                cells[inst_name] = cell
                nets[input_net].loads.append((inst_name, "D"))
                nets[output_net].loads.append((inst_name, "Q"))
                # latch output drives the net
                nets[output_net].driver = (inst_name, "Q")
            continue

    if module_name is None:
        module_name = "top"

    return Netlist(module_name=module_name, ports=ports, nets=nets, cells=cells)


def annotate_net_directions(netlist: Netlist, lib) -> None:
    """Use Liberty library pin directions to fill in netlist.net.driver."""
    for cell in netlist.cells.values():
        lib_cell = lib.cells.get(cell.cell_type)
        if lib_cell is None:
            continue
        for pin_name, pin in cell.pins.items():
            lib_pin = lib_cell.pins.get(pin_name)
            if lib_pin is None:
                continue
            net = netlist.nets.get(pin.net_name)
            if net is None:
                continue
            if lib_pin.direction == "output":
                net.driver = (cell.name, pin_name)
            # input pins are already in loads
