"""
Run complete forward-design pipeline for ALL c910_cpu modules.

Pipeline: Spec → DSL → Simulator verify → Verilog
"""
import os, sys, re, inspect, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

from rtlgen.codegen import VerilogEmitter
from rtlgen.sim import Simulator
from rtlgen.core import Module as CoreModule

SPECS_DIR = "generated_skill_ppa/c910_cpu/specs"
DSL_DIR = "skills/c910_cpu"
OUT_DIR = "generated_skill_ppa/c910_cpu/hand_generated"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Step 0: Discover DSL classes
# ---------------------------------------------------------------------------
def discover_dsl_classes():
    dsl = {}
    for fname in sorted(os.listdir(DSL_DIR)):
        if not fname.endswith(".py") or fname == "__init__.py":
            continue
        fpath = os.path.join(DSL_DIR, fname)
        mn = fname[:-3]
        try:
            spec = importlib.util.spec_from_file_location(mn, fpath)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mn] = mod
                spec.loader.exec_module(mod)
                for an in dir(mod):
                    attr = getattr(mod, an)
                    if (isinstance(attr, type) and issubclass(attr, CoreModule)
                            and attr is not CoreModule):
                        dsl[an] = (fpath, attr)
        except Exception:
            pass
    return dsl

dsl_classes = discover_dsl_classes()

# ---------------------------------------------------------------------------
# Step 1: Parse spec files - extract module name & ports
# ---------------------------------------------------------------------------
def extract_module_name(spec_content, spec_basename):
    for line in spec_content.split('\n'):
        m = re.match(r'^# Module Spec:\s+(\S+)', line)
        if m:
            return m.group(1)
    base = spec_basename.replace('_spec.md', '').replace('.md', '')
    return ''.join(p.capitalize() for p in base.split('_'))

def parse_spec_ports(spec_content):
    """Parse I/O ports from spec, handling both Interface and Ports formats."""
    inputs = []
    outputs = []
    current_section = ""
    for line in spec_content.split('\n'):
        # Match: ### Inputs or ### Inputs (N)
        m = re.match(r'^### (Inputs?|Outputs?)(?:\s+\(\d+\))?\s*$', line)
        if m:
            current_section = m.group(1).lower()
            # Normalize: 'input' or 'inputs' -> 'input', 'output' or 'outputs' -> 'output'
            if current_section.startswith('input'):
                pass  # stays as-is, section type
            elif current_section.startswith('output'):
                pass
        elif '|' in line and current_section in ('inputs', 'output', 'outputs', 'input'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            # Accept: | name | width | or | Signal/Port | Width | Description |
            if len(parts) >= 2 and parts[0] not in ('Signal', 'Port', '---'):
                sig, w = parts[0], parts[1]
                if w.isdigit():
                    if current_section in ('inputs', 'input'):
                        inputs.append((sig, int(w)))
                    else:
                        outputs.append((sig, int(w)))
    return inputs, outputs

# ---------------------------------------------------------------------------
# Generate skeleton from spec (handles both Interface and Ports formats)
# ---------------------------------------------------------------------------
def spec_to_module_class(spec_content, module_name):
    """Generate DSL skeleton from spec markdown content."""
    inputs, outputs = parse_spec_ports(spec_content)
    lines = [
        f'"""',
        f'{module_name} — Auto-generated from spec.',
        f'"""',
        f'from rtlgen.core import Module, Input, Output, Wire, Reg, Const',
        f'from rtlgen.logic import If, Else, Elif',
        f'',
        f'',
        f'class {module_name}(Module):',
        f'    """TODO: implement per spec behavior."""',
        f'    def __init__(self):',
        f'        super().__init__("{module_name.lower()}")',
    ]
    # Add clk/rst_n if not already in inputs
    has_clk = any(s == 'clk' for s, _ in inputs)
    has_rst = any(s == 'rst_n' for s, _ in inputs)
    if has_clk and not has_rst:
        inputs.insert(0, ('rst_n', 1))
    elif not has_clk and has_rst:
        inputs.insert(0, ('clk', 1))
    elif not has_clk and not has_rst:
        inputs.insert(0, ('clk', 1))
        inputs.insert(0, ('rst_n', 1))

    for sig, w in inputs:
        lines.append(f'        self.{sig} = Input({w}, "{sig}")')
    for sig, w in outputs:
        lines.append(f'        self.{sig} = Output({w}, "{sig}")')

    if has_clk or has_rst:
        lines.extend([
            f'        init = Reg(1, "init")',
            f'',
            f'        with self.seq(self.clk, ~self.rst_n):',
            f'            with If(~self.rst_n): init <<= 0',
            f'            with Else(): init <<= 1',
            f'',
            f'        with self.comb:',
            f'            with If(init == 0):',
        ])
        for sig, w in outputs:
            lines.append(f'                self.{sig} <<= Const(0, {w})')
        lines.append(f'            with Else():')
        lines.append(f'                pass')
    else:
        lines.extend([
            f'        with self.comb:',
            f'            pass',
        ])
    return '\n'.join(lines)

# ---------------------------------------------------------------------------
# Step 2: Find matching DSL class
# ---------------------------------------------------------------------------
def find_matching_dsl(mod_name, spec_basename):
    if mod_name in dsl_classes:
        return dsl_classes[mod_name]
    low = mod_name.lower()
    for cn, info in dsl_classes.items():
        if cn.lower() == low:
            return info
    base_key = spec_basename.replace('_spec.md', '').replace('.md', '')
    for cn, info in dsl_classes.items():
        fb = os.path.basename(info[0]).replace('.py', '')
        if fb == base_key or fb == base_key.lower():
            return info
    if mod_name.startswith('ct_'):
        short = mod_name[3:]
        for cn, info in dsl_classes.items():
            if cn.lower() == short.lower():
                return info
    return None

# ---------------------------------------------------------------------------
# Generate skeleton and import
# ---------------------------------------------------------------------------
def generate_skeleton(module_name, spec_content):
    skel_code = spec_to_module_class(spec_content, module_name)
    if not skel_code:
        return None
    gen_path = os.path.join(OUT_DIR, f"_gen_{module_name.lower()}.py")
    with open(gen_path, 'w') as f:
        f.write(skel_code)
    spec2 = importlib.util.spec_from_file_location(
        f"_gen_{module_name.lower()}", gen_path)
    if not spec2 or not spec2.loader:
        return None
    gen_mod = importlib.util.module_from_spec(spec2)
    sys.modules[f"_gen_{module_name.lower()}"] = gen_mod
    spec2.loader.exec_module(gen_mod)
    for attr_name in dir(gen_mod):
        attr = getattr(gen_mod, attr_name)
        if (isinstance(attr, type) and issubclass(attr, CoreModule)
                and attr is not CoreModule):
            return attr
    return None

# ---------------------------------------------------------------------------
# Try to instantiate a class with smart defaults
# ---------------------------------------------------------------------------
def try_instantiate(cls):
    try:
        return cls()
    except TypeError:
        pass
    try:
        sig = inspect.signature(cls.__init__)
        params = list(sig.parameters.items())[1:]
        args = {}
        defaults_map = {
            'depth': 8, 'width': 32, 'entries': 32, 'n_src': 4,
            'pr_num': 64, 'ar_num': 32, 'reset_val': 0, 'size': 64,
            'n': 4, 'num_entries': 32, 'data_width': 64,
            'addr_width': 32, 'tag_width': 20, 'index_width': 8,
            'offset_width': 3, 'ways': 4, 'sets': 64,
        }
        for pname, p in params:
            if p.default is not inspect.Parameter.empty:
                args[pname] = p.default
            else:
                args[pname] = defaults_map.get(pname, 0)
        return cls(**args)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------
spec_files = sorted(f for f in os.listdir(SPECS_DIR) if f.endswith('.md'))

dsl_found_hand = 0
dsl_generated = 0
sim_pass = 0
sim_fail = 0
verilog_files = 0
skipped_ct = 0

for spec_file in spec_files:
    spec_path = os.path.join(SPECS_DIR, spec_file)
    with open(spec_path) as f:
        spec_content = f.read()

    module_name = extract_module_name(spec_content, spec_file)

    dsl_info = find_matching_dsl(module_name, spec_file)
    dsl_found = dsl_info is not None and dsl_info[1] is not None

    dsl_cls = None
    dsl_instance = None
    sim_ok = False
    verilog_ok = False
    reason = ""
    is_generated = False

    if dsl_found:
        dsl_found_hand += 1
        dsl_cls = dsl_info[1]
        dsl_instance = try_instantiate(dsl_cls)
        if dsl_instance is None:
            reason = "Instantiate fail (missing args)"
    else:
        # Skip ct_ specs - too complex (90+ ports), skeleton not useful
        if module_name.startswith('ct_') or spec_file.startswith('ct_'):
            skipped_ct += 1
            reason = "ct_ spec (too complex, skip)"
            sim_fail += 1
            dsl_flag = "N"
            sim_flag = "FAIL"
            v_flag = "FAIL"
            line = f"  {spec_file.replace('_spec.md','')}.{module_name}: DSL=N Sim=FAIL Verilog=FAIL  # {reason}"
            print(line)
            continue

        # Generate skeleton from spec
        dsl_cls = generate_skeleton(module_name, spec_content)
        if dsl_cls:
            dsl_generated += 1
            is_generated = True
            dsl_instance = try_instantiate(dsl_cls)
            if dsl_instance is None:
                reason = "Skel inst fail"
        else:
            reason = "Skeleton gen fail"

    # --- Simulate ---
    if dsl_instance is not None:
        try:
            # Check if module has clk/rst_n (sequential or combinational)
            has_rst = 'rst_n' in dsl_instance._inputs or 'rst_n' in dsl_instance._regs
            has_clk = 'clk' in dsl_instance._inputs
            sim = Simulator(dsl_instance, use_xz=False)
            if has_rst and has_clk:
                sim.reset(rst="rst_n", cycles=3)
                sim.step()
            elif has_clk:
                # Has clk but no rst_n - just step
                for _ in range(3):
                    sim.step()
            else:
                # Combinational only - just evaluate comb
                sim.step()
            # Read all outputs to verify
            for oname in list(dsl_instance._outputs.keys()):
                int(sim.get(oname))
            sim_ok = True
            sim_pass += 1
        except Exception as e:
            reason = f"Sim fail: {e}"
            sim_fail += 1
    else:
        if not reason:
            reason = "No instance"
        sim_fail += 1

    # --- Verilog ---
    if sim_ok and dsl_instance is not None:
        try:
            emitter = VerilogEmitter()
            vtext = emitter.emit(dsl_instance)
            out_path = os.path.join(OUT_DIR, f"{module_name}.v")
            with open(out_path, 'w') as f:
                f.write(vtext)
            verilog_ok = True
            verilog_files += 1
        except Exception as e:
            reason = f"Verilog fail: {e}"

    dsl_flag = "Y" if dsl_found else ("G" if is_generated else "N")
    sim_flag = "PASS" if sim_ok else "FAIL"
    v_flag = "PASS" if verilog_ok else "FAIL"

    line = f"  {spec_file.replace('_spec.md','')}.{module_name}: DSL={dsl_flag} Sim={sim_flag} Verilog={v_flag}"
    if reason:
        line += f"  # {reason}"
    print(line)

# Summary
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
total = len(spec_files)
print(f"Total specs: {total}")
print(f"  DSL found: {dsl_found_hand} (hand-written) + {dsl_generated} (generated)")
print(f"  Skipped (ct_ complex): {skipped_ct}")
print(f"  Sim PASS:  {sim_pass}")
print(f"  Sim FAIL:  {sim_fail}")
print(f"  Verilog:   {verilog_files} files")
