"""
skills.cpu.test_layers — 三层跨层验证.

验证每个模块:
  Layer 1 (Functional) sim PASS
        → guide L1→L2 生成
  Layer 2 (Cycle-Level) sim PASS
        → guide L2→L3 生成  
  Layer 3 (DSL) sim PASS
        → Verilog 生成

跨层一致性: L1 行为 == L2 时序 == L3 RTL 语义
"""
import sys; sys.path.insert(0, '.')
import os
from typing import Any, Callable, Dict, List, Tuple

from rtlgen.forward import design_flow, LayerVerifier
from rtlgen.sim import Simulator


def test_three_layer_flow():
    """对关键模块执行完整三层设计流程."""
    
    results = []
    
    # ================================================================
    # ALU — 算术逻辑单元
    # ================================================================
    print('\n' + '='*60)
    print('ALU — 三层设计验证')
    print('='*60)
    
    # Layer 1: 行为函数 (已存在)
    from skills.cpu.functional import iu_alu_functional
    l1_alu = iu_alu_functional()
    
    # Layer 2: 周期模型 (已存在)
    from skills.cpu.cycle_level import iu_alu_cycle
    
    # Layer 3: DSL 模块 (已存在)
    from skills.cpu.layer3_dsl.alu import ALU
    
    r = design_flow(
        "ALU", "Arithmetic Logic Unit with 10 operations",
        l1_func=l1_alu,
        l1_inputs=[("op",4,"operation code"), ("a",64,"operand A"), ("b",64,"operand B")],
        l1_outputs=[("result",64,"computation result"), ("zero",1,"result is zero")],
        l1_state_vars=[("shamt",7,0,"shift amount from b[6:0]")],
        l2_func=iu_alu_cycle,
        l3_class=ALU,
    )
    results.append(("ALU", r.get("l3_sim","FAIL")))
    
    # ================================================================
    # IBuf — 指令缓冲
    # ================================================================
    print('\n' + '='*60)
    print('IBuf — 三层设计验证')
    print('='*60)
    
    from skills.cpu.cycle_level import ibuf_cycle
    from skills.cpu.layer3_dsl.ibuf import IBuf
    
    r = design_flow(
        "IBuf", "8-entry instruction FIFO with bypass",
        l1_inputs=[("push_valid",1,"push enable"), ("push_data",32,"instruction"),
                    ("pop_ready",1,"pop enable")],
        l1_outputs=[("data",32,"instruction out"), ("valid",1,"output valid"),
                     ("stall",1,"FIFO full")],
        l1_state_vars=[("cnt",4,0,"entry count"), ("wr",3,0,"write pointer"),
                        ("rd",3,0,"read pointer")],
        l2_func=ibuf_cycle,
        l3_class=IBuf,
    )
    results.append(("IBuf", r.get("l3_sim","FAIL")))
    
    # ================================================================
    # ROB — 重排序缓冲
    # ================================================================
    print('\n' + '='*60)
    print('ROB — 三层设计验证')
    print('='*60)
    
    from skills.cpu.functional import rtu_rob_functional
    from skills.cpu.layer3_dsl.rob import ROB
    
    r = design_flow(
        "ROB", "32-entry reorder buffer",
        l1_func=rtu_rob_functional(),
        l1_inputs=[("alloc",1,"allocate entry"), ("complete",1,"mark complete"),
                    ("retire_ready",1,"retire handshake")],
        l1_outputs=[("retire_en",1,"retire valid"), ("full",1,"ROB full"),
                     ("empty",1,"ROB empty")],
        l1_state_vars=[("head",5,0,"retire pointer"), ("tail",5,0,"allocate pointer"),
                        ("cnt",5,0,"entry count")],
        l3_class=ROB,
    )
    results.append(("ROB", r.get("l3_sim","FAIL")))
    
    # ================================================================
    # Summary
    # ================================================================
    print('\n' + '='*60)
    print('三层设计验证汇总')
    print('='*60)
    all_pass = True
    for name, status in results:
        if 'FAIL' in str(status):
            all_pass = False
            print(f'  {name:15s} FAIL — {status}')
        else:
            print(f'  {name:15s} PASS')
    
    if all_pass:
        print(f'\n全部通过: {len(results)}/{len(results)}')
    else:
        print(f'\n有失败: 需检查')
    
    return all_pass


def test_guide_generation():
    """验证 guide 文件生成."""
    os.makedirs("generated_skill_ppa/cpu/guides", exist_ok=True)
    
    from rtlgen.forward import generate_layer_guide
    
    # L1→L2 guide for IBuf
    guide = generate_layer_guide(
        "IBuf", 1,
        [("push_valid",1,"from icache"), ("push_data",32,"instruction"),
         ("pop_ready",1,"from decoder")],
        [("data",32,"to decoder"), ("valid",1,"data valid"), ("stall",1,"backpressure")],
        state_vars=[("cnt",4,0,"entry count"), ("wr",3,0,"write ptr"), ("rd",3,0,"read ptr")],
        behaviors=["Push: store data at wr_ptr, increment wr_ptr and cnt",
                    "Pop: read from rd_ptr, increment rd_ptr, decrement cnt",
                    "Bypass: push data available immediately on same cycle"],
        timing="Pipeline: 1-cycle push-to-pop latency",
        next_layer_hints=[
            "Register: cnt(4), wr(3), rd(3) as Reg in seq block",
            "Array: mem[8][32] for FIFO storage",
            "Bypass: bp_v(1), bp_d(32) register for zero-latency",
        ]
    )
    with open("generated_skill_ppa/cpu/guides/IBuf_L1_guide.md", "w") as f:
        f.write(guide)
    
    print(f'Guide generated: {len(guide.splitlines())} lines')
    print('Guide preview:')
    for line in guide.splitlines()[:15]:
        print(f'  {line}')
    
    return True


if __name__ == '__main__':
    print('='*60)
    print('三层设计流程全线验证')
    print('='*60)
    
    test_guide_generation()
    test_three_layer_flow()
    
    print('\n' + '='*60)
    print('验证产出:')
    print('  guides/   — L1→L2, L2→L3 设计指引')
    print('  Verilog/  — 综合级 RTL')
    print('  每层独立仿真 + 跨层一致性检查')
    print('='*60)
