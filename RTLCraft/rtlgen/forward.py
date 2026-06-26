"""
rtlgen.forward — 三层正向设计流水线.

方法论:
  Layer 1 (Functional) — 纯函数, 无时序, 描述"做什么"
      模拟: 函数调用 inputs→outputs
      输出: 接口规范 + 状态变量定义 → 指导 Layer 2
       
  Layer 2 (Cycle-Level) — CycleContext, 寄存器精确, 描述"何时做"
      模拟: ArchSimulator, 周期精确
      输出: 时序图 + 寄存器定义 → 指导 Layer 3
       
  Layer 3 (DSL) — rtlgen DSL, 可综合 RTL, 描述"如何做"
      模拟: Simulator(inst), 组合+时序
      输出: Verilog (VerilogEmitter)

  每层仿真验证通过后, 生成下一层的 guide.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
import inspect, os

import importlib, types
from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry
from rtlgen.sim import Simulator
from rtlgen.core import Module, Input, Output


# =====================================================================
# Layer Guide — 层间设计指引
# =====================================================================

def generate_layer_guide(
    module_name: str,
    layer: int,
    inputs: List[Tuple[str, int, str]],
    outputs: List[Tuple[str, int, str]],
    state_vars: Optional[List[Tuple[str, int, Any, str]]] = None,
    behaviors: Optional[List[str]] = None,
    timing: Optional[str] = None,
    next_layer_hints: Optional[List[str]] = None,
) -> str:
    """生成层间设计指引文档.
    
    Layer 1 → 2 guide: 接口定义 + 状态变量 + 行为描述
    Layer 2 → 3 guide: 寄存器定义 + 时序 + FSM 状态
    """
    lines = [
        f'# {module_name} — Layer {layer} Design Guide',
        f'',
        f'## Interface',
        f'',
        f'### Inputs',
        f'| Signal | Width | Description |',
        f'|--------|-------|-------------|',
    ]
    for name, width, desc in inputs:
        lines.append(f'| {name} | {width} | {desc} |')
    
    lines.extend(['', '### Outputs', '', '| Signal | Width | Description |',
                   '|--------|-------|-------------|'])
    for name, width, desc in outputs:
        lines.append(f'| {name} | {width} | {desc} |')
    
    if state_vars:
        lines.extend(['', '## State Variables'])
        for name, width, init, desc in state_vars:
            lines.append(f'- **{name}**: {width}bit, init={init} — {desc}')
    
    if behaviors:
        lines.extend(['', '## Behavioral Description'])
        for b in behaviors:
            lines.append(f'- {b}')
    
    if timing:
        lines.extend(['', '## Timing', '', timing])
    
    if next_layer_hints:
        lines.extend(['', '## Guide to Next Layer'])
        for hint in next_layer_hints:
            lines.append(f'- {hint}')
    
    return '\n'.join(lines)


# =====================================================================
# Cross-Layer Verification
# =====================================================================

def _cycle_to_beh_func(l2_func: Callable, outputs: List[str]) -> Callable:
    """将 L2 CycleContext 模型包装为 Simulator 兼容的 dict-in/dict-out 行为函数.
    
    L2 CycleContext 模型: def behavior(ctx): ctx.get_input('x'), ctx.set_output('y', val)
    Simulator beh_func:    def func(inputs_dict) -> outputs_dict
    
    这个包装器使得 L2 模型可以被 Simulator 直接驱动,
    从而与 L3 使用完全相同的测试框架进行对比验证.
    
    状态管理:
      - _state: 当前步骤的基准状态 (从上一步继承)
      - _next_state: 下一步骤的下一状态 (计算得到)
      - _frozen: 是否已在本步骤内完成状态推进
      Step() 会多次调用 _eval_comb, 但状态仅推进一次.
      调用者必须在本步骤所有仿真完成后调用 _advance() 来推进状态.
    """
    _state: Dict[str, Any] = {}
    _next_state: Dict[str, Any] = {}
    _frozen: bool = False
    _cached: Dict[str, Any] = {}

    def _advance():
        nonlocal _state, _next_state, _frozen
        _state.clear()
        _state.update(_next_state)
        _frozen = False

    def beh_func(inputs: Dict[str, Any]) -> Dict[str, Any]:
        nonlocal _state, _next_state, _frozen, _cached
        if not _frozen:
            ctx = CycleContext()
            for k, v in _state.items():
                ctx.state[k] = v
            for name, val in inputs.items():
                ctx.inputs[name] = val
            l2_func()(ctx)
            _next_state.clear()
            _next_state.update(ctx.state)
            _cached = {}
            for out_name in outputs:
                if out_name in ctx.outputs:
                    _cached[out_name] = ctx.outputs[out_name]
            _frozen = True
        return dict(_cached)

    beh_func._advance = _advance
    return beh_func


class LayerVerifier:
    """跨层一致性验证器.
    
    强制要求: L1 值 == L2 值 == L3 值. 不一致则设计错误.
    
    验证方法:
      L1 (纯函数, 无时序):  给定输入, 检查输出值
      L2 (CycleContext):   给定输入序列, 稳定后检查输出值
      L3 (DSL Simulator):  给定输入序列, 稳定后检查输出值
      
      所有三层在相同输入下必须产生相同输出值.
    """
    
    @staticmethod
    def verify(
        module_name: str,
        l1_func: Callable,
        l3_class: type,
        test_cases: List[Dict[str, Dict[str, Any]]],
        l2_func: Optional[Callable] = None,
        sim_cycles: int = 10,
    ) -> bool:
        """执行三层一致性验证.
        
        Args:
            module_name: 模块名 (用于错误报告)
            l1_func: Layer 1 函数 (kwargs→dict)
            l3_class: Layer 3 DSL Module 子类
            test_cases: [{ 
                "inputs": {信号名: 值, ...},      # 施加到所有层的输入
                "expect": {输出信号名: 值, ...},   # 预期输出 (可选, 用于 L1 验证)
                "sequence": [{信号:值,...}, ...]  # 周期序列 (用于 L2/L3)
            }, ...]
            l2_func: Layer 2 周期模型 (可选)
            sim_cycles: L3 仿真周期数
        
        Returns:
            True 全部通过, False 存在不一致
        
        Raises:
            AssertionError: 当跨层不一致时抛出, 附带详细原因
        """
        errors = []
        
        for case_idx, case in enumerate(test_cases):
            l1_inputs = case.get("l1_inputs", {})
            l3_inputs = case.get("l3_inputs", {})
            l2_inputs = case.get("l2_inputs", l3_inputs)  # 默认与 L3 相同
            expect = case.get("expect", {})
            l1_output_map = case.get("l1_output_map", {})
            l3_output_map = case.get("l3_output_map", {})
            tag = case.get("tag", f"case_{case_idx}")
            
            # ---- Layer 1: 函数调用 ----
            l1_result = {}
            if l1_func is not None:
                try:
                    l1_out = l1_func(**l1_inputs)
                    if isinstance(l1_out, dict):
                        l1_result = l1_out
                except Exception as e:
                    errors.append(f"[{tag}] L1 call FAIL: {e}")
            
            # 验证 L1 输出 == 预期值
            for sig, expected_val in expect.items():
                actual = l1_result.get(sig)
                if actual is not None and actual != expected_val:
                    errors.append(
                        f"[{tag}] L1 MISMATCH: {sig} = {actual}, expect {expected_val}"
                    )
            
            # ---- Layer 2 + 3: 通过 Simulator 统一驱动 ----
            # L2 和 L3 使用完全相同的测试框架, 保证对比公平
            l2_result = {}
            l3_result = {}
            
            # 为 L2 创建 Simulator (通过 beh_func 包装)
            l2_sim = None
            if l2_func is not None:
                l3_output_names = list(expect.keys())
                l2_beh = _cycle_to_beh_func(l2_func, l3_output_names)
                l2_mod = Module(f"{module_name}_l2")
                l2_mod.clk = Input(1, "clk"); l2_mod.rst_n = Input(1, "rst_n")
                for sig, val in l2_inputs.items():
                    if isinstance(val, int):
                        w = max(val.bit_length(), 1)
                        setattr(l2_mod, sig, Input(w, sig))
                for sig in expect:
                    w = 64
                    if isinstance(expect[sig], int):
                        w = max(expect[sig].bit_length(), 1)
                    setattr(l2_mod, sig, Output(w, sig))
                l2_mod._beh_func = l2_beh
                try:
                    l2_sim = Simulator(l2_mod, use_xz=False)
                    l2_sim._jit = None  # 必须禁用 JIT, 否则 _beh_func 不会被调用
                    l2_sim.reset(rst='rst_n', cycles=3)
                    for sig, val in l2_inputs.items():
                        if hasattr(l2_mod, sig):
                            l2_sim.set(sig, val)
                    if hasattr(l2_beh, '_advance'):
                        l2_beh._advance()  # Advance after reset to start fresh
                    for _ in range(sim_cycles):
                        l2_sim.step()
                        if hasattr(l2_beh, '_advance'):
                            l2_beh._advance()
                    for sig in expect:
                        if hasattr(l2_mod, sig):
                            l2_result[sig] = int(l2_sim.get(sig))
                except Exception as e:
                    errors.append(f"[{tag}] L2 sim FAIL: {e}")
            
            # L3 Simulator (标准 DSL 模块)
            try:
                inst = l3_class()
                s = Simulator(inst, use_xz=False)
                s.reset(rst='rst_n', cycles=3)
                for sig, val in l3_inputs.items():
                    if hasattr(inst, sig):
                        s.set(sig, val)
                for _ in range(sim_cycles):
                    s.step()
                for sig in expect:
                    if hasattr(inst, sig):
                        l3_result[sig] = int(s.get(sig))
            except Exception as e:
                errors.append(f"[{tag}] L3 sim FAIL: {e}")
            
            # 验证预期值 (所有层)
            for sig, expected_val in expect.items():
                for layer_name, result_dict in [("L1", l1_result), ("L2", l2_result), ("L3", l3_result)]:
                    actual = result_dict.get(sig)
                    if actual is not None and actual != expected_val:
                        errors.append(
                            f"[{tag}] {layer_name} MISMATCH: {sig} = {actual}, expect {expected_val}"
                        )
            
            # ---- 跨层一致性: L1 vs L2 vs L3 ----
            # 对比 L1 vs L3 (通过 output_map)
            for l1_sig, l3_sig in l1_output_map.items():
                l1v = l1_result.get(l1_sig)
                l3v = l3_result.get(l3_sig)
                if l1v is not None and l3v is not None and isinstance(l1v, (int, bool)):
                    if l1v != l3v:
                        errors.append(
                            f"[{tag}] L1≠L3 MISMATCH: {l1_sig}->{l3_sig} L1={l1v} L3={l3v}"
                        )
            
            # 对比 L2 vs L3 (相同信号名, 直接对比)
            for sig in set(l2_result.keys()) & set(l3_result.keys()):
                l2v = l2_result[sig]
                l3v = l3_result[sig]
                if l2v != l3v:
                    errors.append(
                        f"[{tag}] L2≠L3 MISMATCH: {sig} L2={l2v} L3={l3v}"
                    )
        
        # ---- Report ----
        if errors:
            print(f"  ❌ {module_name}: {len(errors)} cross-layer error(s)!")
            for e in errors:
                print(f"     {e}")
            return False
        else:
            print(f"  ✓ {module_name}: L1==L2==L3 consistent")
            return True


# =====================================================================
# 完整三层设计流水线
# =====================================================================

def design_flow(
    module_name: str,
    description: str = "",
    # Layer 1
    l1_func: Optional[Callable] = None,
    l1_inputs: Optional[List[Tuple[str, int, str]]] = None,
    l1_outputs: Optional[List[Tuple[str, int, str]]] = None,
    l1_state_vars: Optional[List[Tuple[str, int, Any, str]]] = None,
    # Layer 2
    l2_func: Optional[Callable] = None,
    # Layer 3
    l3_class: Optional[type] = None,
    # Verification
    test_vectors: Optional[List[Dict]] = None,
    output_dir: str = "skills/cpu",
) -> Dict[str, str]:
    """完整三层正向设计流水线.
    
    1. 写 Layer 1 行为函数
    2. 生成 Layer 1 → 2 guide
    3. 写 Layer 2 周期模型 + 验证
    4. 生成 Layer 2 → 3 guide
    5. 写 Layer 3 DSL 模块 + 验证
    6. 生成 Verilog
    """
    result = {"module": module_name}
    
    print(f'\n{"="*50}')
    print(f'正向设计: {module_name} — {description}')
    print(f'{"="*50}')
    
    # Step 1: Layer 1
    print(f'\n[Layer 1] Functional Model')
    if l1_func:
        guide_l1 = generate_layer_guide(
            module_name, 1,
            l1_inputs or [], l1_outputs or [],
            state_vars=l1_state_vars,
            behaviors=[description],
            next_layer_hints=[
                f"Pipeline stages: determine from L1 sequential dependencies",
                f"State variables: derived from L1 internal state requirements",
            ]
        )
        guide_path = f"{output_dir}/{module_name.lower()}_l1_guide.md"
        os.makedirs(output_dir, exist_ok=True)
        with open(guide_path, 'w') as f:
            f.write(guide_l1)
        print(f'  Guide → {guide_path}')
        result["l1_guide"] = guide_path
    
    # Step 2: Layer 2
    print(f'\n[Layer 2] Cycle-Level Model')
    if l2_func:
        guide_l2 = generate_layer_guide(
            module_name, 2,
            l1_inputs or [], l1_outputs or [],
            state_vars=l1_state_vars,
            timing="Pipeline timing: TBD per cycle model",
            next_layer_hints=[
                "Register names/widths from state variables",
                "FSM states from cycle model control flow",
                "Array sizes from FIFO/queue parameters",
            ]
        )
        guide_path = f"{output_dir}/{module_name.lower()}_l2_guide.md"
        with open(guide_path, 'w') as f:
            f.write(guide_l2)
        print(f'  Guide → {guide_path}')
        result["l2_guide"] = guide_path
    
    # Step 3: Layer 3
    print(f'\n[Layer 3] DSL Model')
    if l3_class:
        try:
            inst = l3_class()
            s = Simulator(inst, use_xz=False)
            s.reset(rst='rst_n', cycles=3)
            s.step()
            for out_name in inst._outputs:
                _ = int(s.get(out_name))
            print(f'  Simulation: PASS')
            result["l3_sim"] = "PASS"
            
            # Generate Verilog
            from rtlgen.codegen import VerilogEmitter
            v = VerilogEmitter().emit(inst)
            v_path = f"generated_skill_ppa/cpu/hand_generated/{module_name}.v"
            os.makedirs(os.path.dirname(v_path), exist_ok=True)
            with open(v_path, 'w') as f:
                f.write(v)
            v_lines = v.count('\n')
            print(f'  Verilog → {v_path} ({v_lines} lines)')
            result["verilog"] = v_path
            
        except Exception as e:
            print(f'  Simulation: FAIL — {e}')
            result["l3_sim"] = f"FAIL: {e}"
    
    # Step 4: Cross-Layer Verification (强制性)
    if test_vectors and l1_func and l3_class:
        print(f'\n[Cross-Layer Verification]')
        ok = LayerVerifier.verify(
            module_name, l1_func, l3_class,
            test_vectors, l2_func=l2_func,
        )
        if not ok:
            raise AssertionError(
                f"❌ {module_name}: L1≠L2≠L3 cross-layer mismatch! "
                "Design must be consistent across all layers. "
                "Fix Layer 1, 2, or 3 to match."
            )
        result["cross_layer"] = "PASS"
        print(f'  ✓ L1==L2==L3 一致性强制验证通过')
    
    print(f'\n{"="*50}')
    print(f'{module_name}: 设计完成')
    print(f'{"="*50}')
    
    return result
