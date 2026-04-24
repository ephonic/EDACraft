import sys
sys.path.insert(0, '.')
import numpy as np
from skills.cpu.npu.core import NeuralAccel
from rtlgen.sim import Simulator
from skills.cpu.npu.frontend.instruction_decode import OP_GEMM

def _encode_instr(opcode, func, rd, rs1, rs2_imm):
    return (opcode << 28) | (func << 24) | (rd << 16) | (rs1 << 8) | (rs2_imm & 0xFF)

def _write_jit_mem(sim, mem_name, data_dict):
    idx = sim._jit.mem_idx[mem_name]
    mem = sim._jit.memories[idx]
    width = sim._jit.mem_widths[idx]
    mask = (1 << width) - 1
    for addr, val in data_dict.items():
        mem[addr] = int(val) & mask

array_size = 32

for k_dim in [2, 3, 4]:
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')
    
    weights = {}
    for r in range(array_size):
        for c in range(array_size):
            weights[r * array_size + c] = 1 if (r == c and r < k_dim) else 0
    _write_jit_mem(sim, 'sram_a_bank0', weights)
    
    activations = {}
    for r in range(array_size):
        for c in range(array_size):
            activations[r * array_size + c] = 1 if (r == c and r < k_dim) else 0
    _write_jit_mem(sim, 'sram_b_bank0', activations)
    
    gemm_instr = _encode_instr(OP_GEMM, func=0, rd=0, rs1=0, rs2_imm=k_dim)
    _write_jit_mem(sim, 'inst_mem_mem', {0: gemm_instr})
    
    sim.poke('prog_length', 1)
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)
    
    for i in range(1000):
        sim.step()
        if sim.peek('prog_done'):
            break
    
    mem = sim._jit.memories[sim._jit.mem_idx['sram_c_bank0']]
    result = np.zeros((k_dim, k_dim), dtype=np.int16)
    for r in range(k_dim):
        for c in range(k_dim):
            v = mem[r * array_size + c]
            result[r, c] = v - 65536 if v > 32767 else v
    
    expected = np.eye(k_dim, dtype=np.int16)
    ok = np.array_equal(result, expected)
    status = "PASS" if ok else "FAIL"
    print(f"k_dim={k_dim}: {status}")
    if not ok:
        print(f"  Result:\n{result}")
        print(f"  Expected:\n{expected}")
