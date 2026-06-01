"""
rtlgen.rtl_analyzer — Analyze reference Verilog to extract module structure.

Extracts from C910 and other ref_rtl designs:
  - Ports (direction, width, name)
  - Sub-module instantiations and port maps
  - State machine constants and registers
  - Always-block types (combinational, sequential)
  - Wire/reg declarations

This data feeds the generation pipeline, replacing hardcoded templates.
"""
import os, re
from typing import Any, Dict, List, Optional, Tuple


def analyze_verilog(filepath: str) -> Dict[str, Any]:
    """Analyze a single Verilog file and extract module structure."""
    with open(filepath) as f:
        content = f.read()

    info = {
        "file": os.path.basename(filepath),
        "module_name": "",
        "ports": [],        # {name, direction, width, type}
        "params": [],       # {name, default}
        "wires": [],        # {name, width}
        "regs": [],         # {name, width, type}
        "submodules": [],   # {name, type, port_map}
        "always_blocks": [], # {type, sensitivity, body_lines}
        "state_regs": [],   # {name, states: [...]}
        "assignments": [],   # {target, expression}
        "comment": "",
    }

    # Remove comments (simple: strip // to end of line)
    clean = re.sub(r'//.*', '', content)
    clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)

    # Module name
    mm = re.search(r'module\s+(\w+)\s*(#\((.*?)\))?\s*\(', clean, re.DOTALL)
    if mm:
        info["module_name"] = mm.group(1)

    # Parse port declarations (C910 style: after module header)
    # Format: "input [msb:lsb] name;" or "input name;"
    for pd in re.finditer(
        r'^\s*(input|output|inout)\s+(wire|reg|logic)?\s*'
        r'(?:\[(\d+)\s*:\s*(\d+)\]\s*)?'
        r'(\w+(?:_\w+)*)\s*;',
        clean, re.MULTILINE
    ):
        direction = pd.group(1)
        msb, lsb = pd.group(3), pd.group(4)
        name = pd.group(5)
        width = int(msb) - int(lsb) + 1 if msb and lsb else 1
        info["ports"].append({
            "name": name, "direction": direction,
            "width": width
        })

    # Wire/reg declarations
    for wm in re.finditer(r'(wire|reg|logic)\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*;', clean):
        kind = wm.group(1)
        msb, lsb = wm.group(2), wm.group(3)
        width = int(msb) - int(lsb) + 1 if msb and lsb else 1
        name = wm.group(4)
        if kind == "reg":
            info["regs"].append({"name": name, "width": width, "type": "reg"})
        else:
            info["wires"].append({"name": name, "width": width})

    # Sub-module instantiations (C910 style: multi-line port maps)
    for sm in re.finditer(r'^(\w+)\s+(?:[xXuU]_)?(\w+)\s*\(', clean, re.MULTILINE):
        mod_type = sm.group(1)
        inst_name = sm.group(2)
        # Skip module declaration itself
        if mod_type == "module": continue
        # Find matching closing paren with semicolon: );
        start = sm.end()
        rest = clean[start:]
        depth, end_pos = 1, 0
        for i, ch in enumerate(rest):
            if ch == '(': depth += 1
            elif ch == ')': depth -= 1
            if depth == 0 and i+1 < len(rest) and rest[i+1] == ';':
                end_pos = start + i + 2
                break
        port_map_str = rest[:end_pos-start-2] if end_pos else rest
        # Skip primitives and known non-module patterns
        if mod_type.lower() in ("if", "else", "for", "wire", "reg", "assign", "always"):
            continue

        # Extract port connections
        port_map = {}
        for pc in re.finditer(r'\.(\w+)\s*\(\s*(\w+)\s*\)', port_map_str):
            port_map[pc.group(1)] = pc.group(2)

        info["submodules"].append({
            "name": inst_name, "type": mod_type,
            "port_map": port_map,
            "line": sm.start()
        })

    # Always blocks
    for ab in re.finditer(
        r'always\s*\@\s*\(([^)]+)\)\s*(?:begin\s*)?(.*?)(?:end|$)',
        clean, re.DOTALL
    ):
        sensitivity = ab.group(1)
        body = ab.group(2)[:200]  # first 200 chars of body
        blk_type = "seq" if "posedge" in sensitivity or "negedge" in sensitivity else "comb"
        info["always_blocks"].append({
            "type": blk_type, "sensitivity": sensitivity.strip(),
            "body_preview": body.strip()[:100]
        })

    # Continuous assignments
    for am in re.finditer(r'assign\s+(\w+)\s*=\s*([^;]+);', clean):
        info["assignments"].append({
            "target": am.group(1), "expression": am.group(2).strip()
        })

    # State machine detection
    for sm in re.finditer(r'localparam\s+(.*?);', clean, re.DOTALL):
        params_str = sm.group(1)
        for pm in re.finditer(r'(\w+)\s*=\s*(\d+)\'[bdh](\w+)', params_str):
            info["params"].append({"name": pm.group(1), "value": pm.group(3)})

    # Detect state registers (regs assigned to constants in always blocks)
    for rm in re.finditer(r'case\s*\((\w+)\)', clean):
        state_reg = rm.group(1)
        # Find state names
        case_body = clean[rm.end():rm.end()+500]
        states = re.findall(r'(\w+)\s*:', case_body)
        if states:
            info["state_regs"].append({"name": state_reg, "states": states})

    return info


def analyze_directory(dirpath: str) -> Dict[str, Dict]:
    """Analyze all Verilog files in a directory tree."""
    results = {}
    for root, dirs, files in os.walk(dirpath):
        for f in sorted(files):
            if not f.endswith(".v"): continue
            filepath = os.path.join(root, f)
            try:
                info = analyze_verilog(filepath)
                results[info["module_name"]] = info
            except Exception as e:
                print(f"  [SKIP] {f}: {e}")
    return results


def generate_module_summary(results: Dict[str, Dict]) -> str:
    """Generate a markdown summary from analyzed modules."""
    lines = ["# C910 Module Analysis Summary", "",
             "| Module | Ports | Sub-modules | Regs | Wires | Always | File |", 
             "|--------|-------|-------------|------|-------|--------|------|"]
    for name, info in sorted(results.items()):
        n_ports = len(info["ports"])
        n_sub = len(info["submodules"])
        n_regs = len(info["regs"])
        n_wires = len(info["wires"])
        n_always = len(info["always_blocks"])
        fname = info["file"]
        lines.append(f"| {name} | {n_ports} | {n_sub} | {n_regs} | {n_wires} | {n_always} | {fname} |")
    return "\n".join(lines)
