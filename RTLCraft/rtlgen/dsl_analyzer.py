"""
rtlgen.dsl_analyzer — Extract structured port/interface/FSM info from hand-written DSL modules.

Loads Module classes from the skill Layer 3 DSL entrypoint and introspects:
  - Port declarations (Input/Output with exact widths)
  - Sub-module instantiations and port maps (from ClusterTop/MeshTop)
  - State registers and array declarations
  - Interface signal patterns
"""
from __future__ import annotations

import importlib.util
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from rtlgen.core import Module, Input, Output, Reg, Wire, Array, SubmoduleInst


def load_dsl_module(skill_name: str) -> Optional[Any]:
    """Load the preferred Layer 3 DSL entrypoint from a skill directory."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        (
            os.path.join(project_root, "skills", skill_name, "dsl_modules.py"),
            f"skills.{skill_name}.dsl_modules",
        ),
        (
            os.path.join(project_root, "skills", skill_name, "layer3_dsl", "__init__.py"),
            f"skills.{skill_name}.layer3_dsl",
        ),
    ]
    dsl_path = None
    full_name = None
    for path, module_name in candidates:
        if os.path.isfile(path):
            dsl_path = path
            full_name = module_name
            break
    if dsl_path is None or full_name is None:
        return None

    spec = importlib.util.spec_from_file_location(full_name, dsl_path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    try:
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def extract_module_ports(mod_cls: type) -> Dict[str, dict]:
    """Instantiate a Module class and extract all Input/Output port definitions."""
    try:
        inst = mod_cls()
    except Exception:
        return {}
    ports = {}
    for name in dir(inst):
        if name.startswith("_"):
            continue
        attr = getattr(inst, name, None)
        if attr is None:
            continue
        if isinstance(attr, Input):
            ports[name] = {"dir": "input", "width": attr.width}
        elif isinstance(attr, Output):
            ports[name] = {"dir": "output", "width": attr.width}
    return ports


def extract_module_state(mod_cls: type) -> Dict[str, list]:
    """Extract Reg/Wire/Array declarations from a Module class."""
    try:
        inst = mod_cls()
    except Exception:
        return {"regs": [], "wires": [], "arrays": []}
    regs = []
    wires = []
    arrays = []
    for name in dir(inst):
        if name.startswith("_"):
            continue
        attr = getattr(inst, name, None)
        if attr is None:
            continue
        if isinstance(attr, Reg):
            regs.append({"name": name, "width": attr.width})
        elif isinstance(attr, Wire):
            wires.append({"name": name, "width": attr.width})
        elif isinstance(attr, Array):
            arrays.append({"name": name, "width": attr.width, "depth": attr.depth})
    return {"regs": regs, "wires": wires, "arrays": arrays}


def extract_submodule_connections(mod_cls: type) -> List[Dict[str, Any]]:
    """Extract SubmoduleInst port maps: how sub-modules connect to parent-level signals."""
    try:
        inst = mod_cls()
    except Exception:
        return []

    connections = []
    for inst_name, sub_mod in getattr(inst, "_submodules", []):
        # The SubmoduleInst object stores the port map
        for entry in getattr(inst, "_top_level", []):
            if isinstance(entry, SubmoduleInst):
                if entry.name == inst_name:
                    for port_name, signal in entry.port_map.items():
                        sig_name = _signal_name(signal)
                        sig_width = _signal_width(signal)
                        connections.append({
                            "submodule": inst_name,
                            "submodule_type": type(sub_mod).__name__,
                            "port": port_name,
                            "connected_to": sig_name,
                            "width": sig_width,
                        })
    return connections


def _signal_name(sig) -> str:
    """Extract name from a Signal/Ref/Wire/Reg object."""
    if hasattr(sig, "_name"):
        return sig._name
    if hasattr(sig, "name"):
        return sig.name
    return str(sig)


def _signal_width(sig) -> int:
    """Extract width from a signal."""
    if hasattr(sig, "width"):
        w = sig.width
        return int(w) if isinstance(w, (int, float)) else str(w)
    return "?"


def build_port_database(skill_name: str) -> Dict[str, Any]:
    """Build a complete database of all modules, ports, and sub-module connections.
    
    Returns:
        {
            "ports": {module_name: {port_name: {"dir": "input", "width": 64}}},
            "state": {module_name: {"regs": [...], "wires": [...], "arrays": [...]}},
            "connections": {module_name: [{submodule, port, connected_to, width}]},
            "interface_map": {module_name: {port_name: {"direction": "in/out", 
                                                         "connected_module": "...",
                                                         "connected_port": "..."}}},
        }
    """
    dsl_mod = load_dsl_module(skill_name)
    if dsl_mod is None:
        return {"ports": {}, "state": {}, "connections": {}, "interface_map": {}}

    dsl_module_name = dsl_mod.__name__
    ports_db = {}
    state_db = {}
    conn_db = {}

    # Find all Module classes defined in this module
    for attr_name in dir(dsl_mod):
        attr = getattr(dsl_mod, attr_name)
        if isinstance(attr, type) and issubclass(attr, Module) and attr is not Module:
            mod_name = getattr(attr, "__module__", "")
            if mod_name == dsl_module_name or mod_name.startswith(f"{dsl_module_name}."):
                name = attr.__name__
                ports_db[name] = extract_module_ports(attr)
                state_db[name] = extract_module_state(attr)
                conns = extract_submodule_connections(attr)
                if conns:
                    conn_db[name] = conns

    # Build interface map: for each port, determine what it connects to
    # This is best-effort: we can see connections in sub-module parents
    interface_map = {}
    for parent_name, conns in conn_db.items():
        for c in conns:
            sub_type = c["submodule_type"]
            port = c["port"]
            connected_to = c["connected_to"]
            if sub_type not in interface_map:
                interface_map[sub_type] = {}
            # Determine direction from the sub-module's own port db
            if sub_type in ports_db and port in ports_db[sub_type]:
                direction = ports_db[sub_type][port]["dir"]
            else:
                direction = "?"
            interface_map[sub_type][port] = {
                "direction": direction,
                "connected_module": parent_name,
                "connected_signal": connected_to,
                "width": c["width"],
            }

    return {
        "ports": ports_db,
        "state": state_db,
        "connections": conn_db,
        "interface_map": interface_map,
    }


def get_port_widths_by_type(pe_type: str, port_db: Dict) -> Dict[str, int]:
    """Get port widths for a given PE type (not instance name).
    
    Maps pe_type (e.g. 'rv64_core') to the corresponding DSL class name
    (e.g. 'RV64Core') and returns port widths.
    """
    # Map from pe_type to DSL class name
    type_to_class = {
        "rv64_core": "RV64Core",
        "l1_cache": "L1Cache",
        "coherence_dir": "CoherenceDir",
        "l2_cache": "L2CacheSlice",
        "noc_router": "NoCRouter",
        "noc_buffer": "NoCBuffer",
        "cluster": "ClusterTop",
        "mesh_top": "MeshTop",
        "ifu": "IFU",
        "idu": "IDU",
        "alu": "ALU",
        "lsu": "LSU",
        "wb": "WB",
    }
    class_name = type_to_class.get(pe_type, "")
    if class_name in port_db:
        return {name: info["width"] for name, info in port_db[class_name].items()}
    return {}


def get_submodule_interactions(pe_type: str, port_db: Dict) -> List[Dict[str, str]]:
    """Get interaction descriptions: which ports connect to which modules.
    
    For a given PE type (e.g. 'rv64_core'), returns a list of:
      { "port": "icache_req", "direction": "output", "connects_to": "L1Cache.req",
        "protocol": "valid/ready handshake" }
    """
    type_to_class = {
        "rv64_core": "RV64Core",
        "l1_cache": "L1Cache",
        "noc_router": "NoCRouter",
        "coherence_dir": "CoherenceDir",
        "l2_cache": "L2CacheSlice",
        "cluster": "ClusterTop",
    }
    class_name = type_to_class.get(pe_type, "")
    interface_map = port_db.get("interface_map", {})

    # For sub-modules, return interface info
    submod_info = interface_map.get(class_name, {})
    results = []
    for port_name, info in submod_info.items():
        entry = {
            "port": port_name,
            "direction": info.get("direction", "?"),
            "connects_to": f"{info.get('connected_module', '?')}.{info.get('connected_signal', '?')}",
            "width": info.get("width", "?"),
        }
        # Infer protocol from signal names
        sig_name = info.get("connected_signal", "")
        if any(kw in sig_name for kw in ["valid", "ready", "req"]):
            entry["protocol"] = "valid/ready handshake"
        elif any(kw in port_name for kw in ["valid", "ready", "req"]):
            entry["protocol"] = "valid/ready handshake"
        else:
            entry["protocol"] = "data/control"
        results.append(entry)
    return results
