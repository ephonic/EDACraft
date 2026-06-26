"""
Micro-architecture extraction tool.
Scans ref_rtl/ Verilog/SystemVerilog files → structured specs in skills/.
"""
import os, re, sys, json
from typing import Dict, List, Optional

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_RTL = os.path.join(REPO, "ref_rtl")
SKILLS = os.path.join(REPO, "skills")

DOMAIN_MAP = {
    "axi": "interfaces/axi", "axil": "interfaces/axi_lite",
    "axis": "interfaces/axis", "i2c": "interfaces/i2c",
    "uart": "interfaces/uart", "spi": "interfaces/spi",
    "pcie": "interfaces/pcie", "ethernet": "interfaces/ethernet",
    "wishbone": "interfaces/wishbone", "btle": "interfaces/btle",
    "dsp": "dsp", "fft": "fft", "cam": "mem/cam",
    "ddr3": "mem/ddr3", "npu": "npu", "noc": "noc",
    "gpgpu": "gpgpu", "cpu": "cpu",
    "fpga-npu": "npu", "rng": "fundamentals",
    "xk265": "codec/video", "LDPC_Decoder": "codec/ldpc",
    "ISP": "image/isp",
}


def extract_module_info(text: str) -> dict:
    """Extract module name, parameters, ports, FSM, hierarchy from Verilog."""
    text = re.sub(r'//.*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    
    result = {
        'module': None, 'lines': 0, 'params': [], 'ports': [],
        'fsm': [], 'children': [], 'always': [], 'localparams': []
    }
    
    m = re.search(r'module\s+(\w+)\s*(?:#|;)', text)
    if not m:
        m = re.search(r'module\s+(\w+)\s*\(', text)
    if not m:
        return result
    result['module'] = m.group(1)
    
    # Parameters
    for pm in re.finditer(
        r'parameter\s+(?:integer\s+)?(\w+)\s*=\s*([^;,\n]+)',
        text
    ):
        result['params'].append({'name': pm.group(1), 'default': pm.group(2).strip()})
    
    # Localparams (FSM states)
    for lm in re.finditer(
        r'localparam\s+(?:integer\s+)?(\w+)\s*=\s*(\d+)',
        text
    ):
        result['localparams'].append((lm.group(1), int(lm.group(2))))
    state_like = [n for n, v in result['localparams']
                  if v < 20 and n.upper() == n]  # ALL_CAPS with small values = FSM
    result['fsm'] = state_like
    
    # Ports
    port_section = ''
    m2 = re.search(r'module\s+\w+\s*#\s*\(([^)]+)\)\s*\(([^)]+)\)', text, re.DOTALL)
    if m2:
        port_section = m2.group(2)
    else:
        m3 = re.search(r'module\s+\w+\s*\(([^)]+)\)', text, re.DOTALL)
        if m3:
            port_section = m3.group(1)
    
    for port_line in port_section.split('\n'):
        pm = re.search(
            r'(input|output|inout)\s+(wire|reg|logic)?\s*(?:\[([^\]]+)\])?\s*(\w+)',
            port_line
        )
        if pm:
            we = pm.group(3) or '1'
            result['ports'].append({
                'dir': pm.group(1), 'width': we, 'name': pm.group(4)
            })
    
    # Hierarchical instantiations (uppercase module names = known IPs)
    for hm in re.finditer(
        r'([A-Z]\w+)\s+#?\s*\(\s*\.(\w+)', text
    ):
        mod = hm.group(1)
        if mod not in ('If', 'Case', 'For', 'End', 'Begin', 'Wire', 'Reg',
                       'Input', 'Output', 'Module', 'Assign', 'Always'):
            result['children'].append({'type': mod, 'port': hm.group(2)})
    
    # Always block types
    for am in re.finditer(r'always\s*@\s*\(([^)]*)\)', text):
        sens = am.group(1)
        if 'posedge' in sens and 'negedge' in sens:
            result['always'].append('seq_async_reset')
        elif 'posedge' in sens:
            result['always'].append('seq')
        elif '*' in sens:
            result['always'].append('comb')
    
    for am in re.finditer(r'(always_comb|always_ff|always_latch)', text):
        result['always'].append(am.group(1))
    
    result['lines'] = len(text.splitlines())
    return result


def gen_markdown(info: dict) -> str:
    md = [f"# {info['module']}"]
    
    # Parameters
    if info['params']:
        md.append("\n## Parameters")
        for p in info['params']:
            md.append(f"- `{p['name']} = {p['default']}`")
    
    # Ports
    if info['ports']:
        md.append(f"\n## Ports ({len(info['ports'])})")
        for p in info['ports']:
            md.append(f"- `{p['dir']} [{p['width']}] {p['name']}`")
    
    # FSM
    if info['fsm']:
        md.append("\n## FSM States")
        for i, s in enumerate(info['fsm']):
            md.append(f"- `{s}` = {i}")
    
    # Children
    if info['children']:
        md.append("\n## Submodule Instances")
        seen = set()
        for c in info['children']:
            key = f"{c['type']}:{c['port']}"
            if key not in seen:
                seen.add(key)
                md.append(f"- `{c['type']}`")
    
    # Always blocks
    if info['always']:
        md.append("\n## Logic Block Types")
        for t in sorted(set(info['always'])):
            md.append(f"- {t}")
    
    return '\n'.join(md) + '\n'


def process_domain(domain: str) -> List[dict]:
    ref_dir = os.path.join(REF_RTL, domain)
    if not os.path.isdir(ref_dir):
        return []
    
    # Find RTL files
    files = []
    for root, _, fnames in os.walk(ref_dir):
        for f in fnames:
            if f.endswith(('.v', '.sv')) and 'tb_' not in f and 'test_' not in f:
                files.append(os.path.join(root, f))
    # Also include testbench files for reference
    for root, _, fnames in os.walk(ref_dir):
        for f in fnames:
            if f.endswith(('.v', '.sv')) and ('tb_' in f or 'test_' in f):
                if f not in files:
                    files.append(os.path.join(root, f))
    
    skill_subdir = DOMAIN_MAP.get(domain, domain)
    spec_dir = os.path.join(SKILLS, skill_subdir, 'specs')
    os.makedirs(spec_dir, exist_ok=True)
    
    results = []
    for fp in files:
        try:
            with open(fp, errors='ignore') as f:
                text = f.read()
            info = extract_module_info(text)
            if not info['module']:
                continue
            info['file'] = os.path.relpath(fp, REPO)
            results.append(info)
            md = gen_markdown(info)
            with open(os.path.join(spec_dir, f"{info['module']}.md"), 'w') as f:
                f.write(md)
        except Exception as e:
            print(f"  SKIP {os.path.basename(fp)}: {e}")
    
    # Domain index
    if results:
        idx = []
        for r in sorted(results, key=lambda x: x['module']):
            idx.append({
                'module': r['module'], 'file': r['file'],
                'lines': r['lines'], 'ports': len(r['ports']),
                'params': len(r['params']), 'fsm': len(r['fsm']),
                'children': len(r['children']),
            })
        with open(os.path.join(spec_dir, '_index.json'), 'w') as f:
            json.dump(idx, f, indent=2)
        print(f"  {domain}: {len(idx)} modules → {spec_dir}/")
    
    return results


def main():
    domains = sorted([d for d in os.listdir(REF_RTL)
                     if os.path.isdir(os.path.join(REF_RTL, d)) and not d.startswith('.')])
    
    if '--domain' in sys.argv:
        idx = sys.argv.index('--domain')
        domains = [sys.argv[idx + 1]]
    
    total = 0
    for domain in domains:
        results = process_domain(domain)
        total += len(results)
    print(f"\nTotal: {total} modules documented")

if __name__ == '__main__':
    main()
