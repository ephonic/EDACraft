"""
rtlgen.spec_gen — Spec Markdown 生成器.

从模块架构描述生成结构化 Spec Markdown 文件.
Spec 由 AI agent 补全功能细节后, 驱动代码生成.
"""
import os
from typing import Dict, List, Tuple, Any, Optional


def generate_spec(
    module_name: str,
    description: str,
    inputs: List[Tuple[str, int, str]],
    outputs: List[Tuple[str, int, str]],
    parameters: Optional[Dict[str, Any]] = None,
    behavior_stub: str = "TODO: describe behavior",
    timing_stub: str = "TODO: describe timing",
    submodules: Optional[List[str]] = None,
    output_dir: str = "generated_skill_ppa/c910_cpu/specs",
) -> str:
    """生成模块 Spec Markdown 文件.
    
    Args:
        module_name: 模块名
        description: 模块功能描述
        inputs: [(信号名, 位宽, 描述), ...]
        outputs: [(信号名, 位宽, 描述), ...]
        parameters: 参数 dict
        behavior_stub: 行为描述 (或 "TODO" 占位)
        timing_stub: 时序描述 (或 "TODO" 占位)
        submodules: 子模块列表
        output_dir: 输出目录
    Returns:
        Spec 文本
    """
    lines = [
        f'# Module Spec: {module_name}',
        f'',
        f'## Module Info',
        f'',
        f'- **Name:** {module_name}',
        f'- **Description:** {description}',
    ]
    
    if parameters:
        lines.extend(['', '## Parameters'])
        for name, val in parameters.items():
            lines.append(f'- **{name}:** {val}')
    
    lines.extend([
        '',
        '## Interface',
        '',
        '### Inputs',
        '',
        '| Signal | Width | Description |',
        '|--------|-------|-------------|',
    ])
    for name, width, desc in inputs:
        lines.append(f'| {name} | {width} | {desc} |')
    
    lines.extend([
        '',
        '### Outputs',
        '',
        '| Signal | Width | Description |',
        '|--------|-------|-------------|',
    ])
    for name, width, desc in outputs:
        lines.append(f'| {name} | {width} | {desc} |')
    
    if submodules:
        lines.extend(['', '## Sub-modules'])
        for s in submodules:
            lines.append(f'- {s}')
    
    lines.extend([
        '',
        '## Behavior',
        '',
        behavior_stub,
        '',
        '## Timing',
        '',
        timing_stub,
        '',
        '---',
        '',
        '*This spec was auto-generated. AI agent should complete the Behavior and Timing sections.*',
    ])
    
    content = '\n'.join(lines)
    
    os.makedirs(output_dir, exist_ok=True)
    fpath = f"{output_dir}/{module_name.lower()}_spec.md"
    with open(fpath, 'w') as f:
        f.write(content)
    
    return content


def spec_to_module_class(spec_content: str) -> str:
    """从 Spec Markdown 生成 DSL 代码骨架.
    
    实际使用中由 AI agent 读取 spec 后补全代码.
    这里仅生成骨架.
    """
    # 解析 spec 提取模块名和端口
    name = ""
    inputs = []
    outputs = []
    for line in spec_content.split('\n'):
        if line.startswith('# Module Spec: '):
            name = line[len('# Module Spec: '):]
    
    lines = [
        f'"""',
        f'{name} — Auto-generated from spec.',
        f'"""',
        f'from rtlgen.core import Module, Input, Output, Wire, Reg, Const',
        f'from rtlgen.logic import If, Else, Elif',
        f'',
        f'',
        f'class {name}(Module):',
        f'    """TODO: implement per spec behavior."""',
        f'    def __init__(self):',
        f'        super().__init__("{name.lower()}")',
        f'        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")',
    ]
    # 从 spec 表格中提取端口
    in_section = ""
    for line in spec_content.split('\n'):
        if line.startswith('### '):
            in_section = line[4:].strip()
        elif '|' in line and in_section in ('Inputs', 'Outputs'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2 and parts[0] not in ('Signal', '---'):
                sig, w = parts[0], parts[1]
                if w.isdigit():
                    if in_section == 'Inputs':
                        inputs.append((sig, int(w)))
                    else:
                        outputs.append((sig, int(w)))
    
    for sig, w in inputs:
        lines.append(f'        self.{sig} = Input({w}, "{sig}")')
    for sig, w in outputs:
        lines.append(f'        self.{sig} = Output({w}, "{sig}")')
    
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
    lines.append(f'                # TODO: implement behavior per spec')
    lines.append(f'                pass')
    lines.append(f'')
    
    return '\n'.join(lines)
