"""
Spec2RTL Design Flow: NoC — 8x8 Mesh Network-on-Chip (XY Routing)
==================================================================

Architecture: 8x8 mesh NoC with 5-port routers (E, W, N, S, Inject/Eject).
Reference: ref_rtl/noc (open-source Verilog NoC implementation).

Global parameters:
  - FLIT_WIDTH = 64
  - X_WIDTH = 3, Y_WIDTH = 3  → 8x8 mesh
  - BUFFER_DEPTH = 4
  - NUM_PORTS = 5 (E=0, W=1, N=2, S=3, Inject/Eject=4)

Hierarchy:
  Network (8x8 mesh)
    └── Process_Node[0..63]
          └── Router (5-port)
                ├── input_Unit[5]  (Buffer + Route_Func + FSM)
                ├── output_unit[5] (Buffer + write_req logic)
                ├── CrossBar       (5x5)
                ├── VC_Alloc       (Virtual Channel Allocator)
                ├── Select_gen     (Crossbar select generator)
                ├── set_Alloc      (Allocation setter)
                ├── ST_Controler   (Switch Traversal controller)
                ├── out_en_gen     (Output enable generator)
                └── ST             (Switch Traversal flags)
"""

from __future__ import annotations
import os, sys
_sys = sys
_sys.setrecursionlimit(10000)

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc, CycleContext,
    InterconnectSpec, HandshakeSpec, QueueSpec, ArchDefinition,
    ArchSimulator, ArchSkeletonGenerator,
)
from rtlgen.core import (
    Module, Input, Output, Wire, Reg, Array, Const, Mux,
    ForGenNode, GenVar,
)
from rtlgen import Cat
from rtlgen.logic import If, Else, Switch, ForGen
from rtlgen.codegen import VerilogEmitter, EmitProfile

try:
    from rtlgen.lint import VerilogLinter
except ImportError:
    VerilogLinter = None

# ============================================================================
# Global Parameters
# ============================================================================
FLIT_WIDTH = 64
X_WIDTH = 3
Y_WIDTH = 3
MESH_SIZE = 8
BUFFER_DEPTH = 4
BUF_ADDR_WIDTH = 2
NUM_PORTS = 5

PORT_E = 0
PORT_W = 1
PORT_N = 2
PORT_S = 3
PORT_INJ = 4

# Flit type encoding
FLIT_HEAD = 0b00
FLIT_BODY = 0b01
FLIT_TAIL = 0b10
FLIT_SINGLE = 0b11

# ============================================================================
# Phase 0: Architecture Definition
# ============================================================================
print("=" * 70)
print("NoC — Phase 0: Architecture Definition")
print("=" * 70)

router_pe = ProcessingElement(
    name="Router",
    pe_type="router",
    inputs=[
        PortDesc("clk", "input", 1),
        PortDesc("reset", "input", 1),
        PortDesc("X_cur", "input", X_WIDTH),
        PortDesc("Y_cur", "input", Y_WIDTH),
        PortDesc("ie", "input", FLIT_WIDTH),
        PortDesc("iw", "input", FLIT_WIDTH),
        PortDesc("in_", "input", FLIT_WIDTH),
        PortDesc("is_", "input", FLIT_WIDTH),
        PortDesc("inject", "input", FLIT_WIDTH),
        PortDesc("push_e", "input", 1),
        PortDesc("push_w", "input", 1),
        PortDesc("push_n", "input", 1),
        PortDesc("push_s", "input", 1),
        PortDesc("push_j", "input", 1),
        PortDesc("e_state", "input", 1),
        PortDesc("w_state", "input", 1),
        PortDesc("n_state", "input", 1),
        PortDesc("s_state", "input", 1),
        PortDesc("eject_state", "input", 1),
        PortDesc("w_e_ack", "input", 1),
        PortDesc("w_w_ack", "input", 1),
        PortDesc("w_n_ack", "input", 1),
        PortDesc("w_s_ack", "input", 1),
        PortDesc("w_j_ack", "input", 1),
    ],
    outputs=[
        PortDesc("oe", "output", FLIT_WIDTH),
        PortDesc("ow", "output", FLIT_WIDTH),
        PortDesc("on_", "output", FLIT_WIDTH),
        PortDesc("os_", "output", FLIT_WIDTH),
        PortDesc("eject", "output", FLIT_WIDTH),
        PortDesc("write_req_e", "output", 1),
        PortDesc("write_req_w", "output", 1),
        PortDesc("write_req_n", "output", 1),
        PortDesc("write_req_s", "output", 1),
        PortDesc("write_req_j", "output", 1),
        PortDesc("e_e", "output", 1),
        PortDesc("w_e", "output", 1),
        PortDesc("n_e", "output", 1),
        PortDesc("s_e", "output", 1),
        PortDesc("j_e", "output", 1),
        PortDesc("push_e_ack", "output", 1),
        PortDesc("push_w_ack", "output", 1),
        PortDesc("push_n_ack", "output", 1),
        PortDesc("push_s_ack", "output", 1),
        PortDesc("push_j_ack", "output", 1),
    ],
    state=[
        StateDesc("oe_f", "int", "East output flag", rtl_type="reg", rtl_width=1),
        StateDesc("ow_f", "int", "West output flag", rtl_type="reg", rtl_width=1),
        StateDesc("on_f", "int", "North output flag", rtl_type="reg", rtl_width=1),
        StateDesc("os_f", "int", "South output flag", rtl_type="reg", rtl_width=1),
        StateDesc("eject_f", "int", "Eject output flag", rtl_type="reg", rtl_width=1),
    ],
    can_stall=False,
    latency=1,
)

network_pe = ProcessingElement(
    name="Network",
    pe_type="network",
    inputs=[
        PortDesc("clk", "input", 1),
        PortDesc("reset", "input", 1),
    ] + [PortDesc(f"inj_{i}", "input", FLIT_WIDTH) for i in range(MESH_SIZE * MESH_SIZE)]
      + [PortDesc(f"push_j_{i}", "input", 1) for i in range(MESH_SIZE * MESH_SIZE)]
      + [PortDesc(f"w_j_ack_{i}", "input", 1) for i in range(MESH_SIZE * MESH_SIZE)],
    outputs=[
        PortDesc(f"ej_{i}", "output", FLIT_WIDTH) for i in range(MESH_SIZE * MESH_SIZE)
    ] + [PortDesc(f"write_req_j_{i}", "output", 1) for i in range(MESH_SIZE * MESH_SIZE)]
      + [PortDesc(f"j_e_{i}", "output", 1) for i in range(MESH_SIZE * MESH_SIZE)]
      + [PortDesc(f"push_j_ack_{i}", "output", 1) for i in range(MESH_SIZE * MESH_SIZE)],
    can_stall=False,
    latency=1,
)

arch = ArchDefinition(
    name="NoC_8x8_Mesh",
    description="8x8 mesh Network-on-Chip with XY routing and 5-port routers",
    isa="protocol",
    processing_elements=[router_pe, network_pe],
    interconnects=[],
    ppa_targets={"max_area": 100000, "target_freq": 500e6},
)

print(f"ArchDefinition built: {len(arch.processing_elements)} PEs")

# ============================================================================
# Phase 1: Architecture Simulation
# ============================================================================
print("\n" + "=" * 70)
print("NoC — Phase 1: Architecture Simulation")
print("=" * 70)

sim = ArchSimulator(arch)
results = sim.run(num_cycles=10, init_inputs={"reset": 0})
print(f"Simulation completed: {len(results)} cycles")

# ============================================================================
# Phase 2: Skeleton Generation
# ============================================================================
print("\n" + "=" * 70)
print("NoC — Phase 2: DSL Skeleton Generation")
print("=" * 70)

gen = ArchSkeletonGenerator()
packages = gen.generate_all(arch)
print(f"Generated {len(packages)} agent packages")

# ============================================================================
# Phase 3: DSL Implementation
# ============================================================================
print("\n" + "=" * 70)
print("NoC — Phase 3: DSL Implementation")
print("=" * 70)

# ---------------------------------------------------------------------------
# Buffer: 4-depth FIFO
# ---------------------------------------------------------------------------
class Buffer(Module):
    def __init__(self):
        super().__init__("buffer")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")
        self.pop = Input(1, "pop")
        self.push = Input(1, "push")
        self.bf_in = Input(FLIT_WIDTH, "bf_in")
        self.bf_out = Output(FLIT_WIDTH, "bf_out")
        self.em_pl = Output(3, "em_pl")  # empty slots

        self._bf = Array(FLIT_WIDTH, BUFFER_DEPTH, "bf")
        self._add_wr = Reg(BUF_ADDR_WIDTH, "add_wr")
        self._add_rd = Reg(BUF_ADDR_WIDTH, "add_rd")

        with self.seq(self.clk, self.reset):
            with If(self.reset == 1):
                for i in range(BUFFER_DEPTH):
                    self._bf[i] <<= 0
                self._add_wr <<= 0
                self._add_rd <<= 0
            with Else():
                with If(self.push == 1 and self.pop == 0):
                    self._bf[self._add_wr] <<= self.bf_in
                    self._add_wr <<= self._add_wr + 1
                with Else():
                    with If(self.push == 0 and self.pop == 1):
                        self._add_rd <<= self._add_rd + 1
                    with Else():
                        with If(self.push == 1 and self.pop == 1):
                            self._bf[self._add_wr] <<= self.bf_in
                            self._add_wr <<= self._add_wr + 1
                            self._add_rd <<= self._add_rd + 1

        with self.comb:
            self.bf_out <<= self._bf[self._add_rd]
            # em_pl = BUFFER_DEPTH - (wr - rd) mod BUFFER_DEPTH
            diff = Wire(3, "diff")
            diff <<= self._add_wr - self._add_rd
            self.em_pl <<= Const(BUFFER_DEPTH, 3) - diff

print("  - Buffer defined")

# ---------------------------------------------------------------------------
# Counter: modulo-5 counter for VC allocation round-robin
# ---------------------------------------------------------------------------
class Counter(Module):
    def __init__(self):
        super().__init__("counter")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")
        self.en = Input(1, "en")
        self.c = Output(3, "c")

        self._cnt = Reg(3, "cnt")
        with self.seq(self.clk, self.reset):
            with If(self.reset == 1):
                self._cnt <<= 0
            with Else():
                with If(self.en == 1):
                    with If(self._cnt == 4):
                        self._cnt <<= 0
                    with Else():
                        self._cnt <<= self._cnt + 1
        with self.comb:
            self.c <<= self._cnt

print("  - Counter defined")

# ---------------------------------------------------------------------------
# Route_Func: XY routing
# ---------------------------------------------------------------------------
class RouteFunc(Module):
    def __init__(self):
        super().__init__("route_func")
        self.X_cur = Input(X_WIDTH, "X_cur")
        self.Y_cur = Input(Y_WIDTH, "Y_cur")
        self.X_dest = Input(X_WIDTH, "X_dest")
        self.Y_dest = Input(Y_WIDTH, "Y_dest")
        self.reset = Input(1, "reset")
        self.valid_out = Output(5, "valid_out")  # [E,W,N,S,Eject]
        self.status = Output(5, "status")

        with self.comb:
            with If(self.reset == 1):
                self.valid_out <<= 0
                self.status <<= 0
            with Else():
                self.valid_out <<= 0
                self.status <<= 0
                with If(self.X_cur < self.X_dest):
                    self.valid_out <<= 1 << PORT_E
                with Else():
                    with If(self.X_cur > self.X_dest):
                        self.valid_out <<= 1 << PORT_W
                    with Else():
                        with If(self.Y_cur < self.Y_dest):
                            self.valid_out <<= 1 << PORT_N
                        with Else():
                            with If(self.Y_cur > self.Y_dest):
                                self.valid_out <<= 1 << PORT_S
                            with Else():
                                self.valid_out <<= 1 << PORT_INJ

print("  - RouteFunc defined")

# ---------------------------------------------------------------------------
# CrossBar: 5x5 crossbar
# ---------------------------------------------------------------------------
class CrossBar(Module):
    def __init__(self):
        super().__init__("crossbar")
        self.S_E = Input(3, "S_E")
        self.S_W = Input(3, "S_W")
        self.S_N = Input(3, "S_N")
        self.S_S = Input(3, "S_S")
        self.S_Ejec = Input(3, "S_Ejec")
        self.IE = Input(FLIT_WIDTH, "IE")
        self.IW = Input(FLIT_WIDTH, "IW")
        self.IN = Input(FLIT_WIDTH, "IN")
        self.IS = Input(FLIT_WIDTH, "IS")
        self.Inject = Input(FLIT_WIDTH, "Inject")
        self.OE = Output(FLIT_WIDTH, "OE")
        self.OW = Output(FLIT_WIDTH, "OW")
        self.ON = Output(FLIT_WIDTH, "ON")
        self.OS = Output(FLIT_WIDTH, "OS")
        self.Eject = Output(FLIT_WIDTH, "Eject")

        with self.comb:
            with Switch(self.S_E) as sw:
                with sw.case(0): self.OE <<= self.IE
                with sw.case(1): self.OE <<= self.IW
                with sw.case(2): self.OE <<= self.IN
                with sw.case(3): self.OE <<= self.IS
                with sw.case(4): self.OE <<= self.Inject
                with sw.default(): self.OE <<= 0
            with Switch(self.S_W) as sw:
                with sw.case(0): self.OW <<= self.IE
                with sw.case(1): self.OW <<= self.IW
                with sw.case(2): self.OW <<= self.IN
                with sw.case(3): self.OW <<= self.IS
                with sw.case(4): self.OW <<= self.Inject
                with sw.default(): self.OW <<= 0
            with Switch(self.S_N) as sw:
                with sw.case(0): self.ON <<= self.IE
                with sw.case(1): self.ON <<= self.IW
                with sw.case(2): self.ON <<= self.IN
                with sw.case(3): self.ON <<= self.IS
                with sw.case(4): self.ON <<= self.Inject
                with sw.default(): self.ON <<= 0
            with Switch(self.S_S) as sw:
                with sw.case(0): self.OS <<= self.IE
                with sw.case(1): self.OS <<= self.IW
                with sw.case(2): self.OS <<= self.IN
                with sw.case(3): self.OS <<= self.IS
                with sw.case(4): self.OS <<= self.Inject
                with sw.default(): self.OS <<= 0
            with Switch(self.S_Ejec) as sw:
                with sw.case(0): self.Eject <<= self.IE
                with sw.case(1): self.Eject <<= self.IW
                with sw.case(2): self.Eject <<= self.IN
                with sw.case(3): self.Eject <<= self.IS
                with sw.case(4): self.Eject <<= self.Inject
                with sw.default(): self.Eject <<= 0

print("  - CrossBar defined")

# ---------------------------------------------------------------------------
# ST: Switch Traversal enable (AND gates)
# ---------------------------------------------------------------------------
class ST(Module):
    def __init__(self):
        super().__init__("st")
        self.e_req = Input(1, "e_req")
        self.w_req = Input(1, "w_req")
        self.n_req = Input(1, "n_req")
        self.s_req = Input(1, "s_req")
        self.eject_req = Input(1, "eject_req")
        self.oe_f = Input(1, "oe_f")
        self.ow_f = Input(1, "ow_f")
        self.on_f = Input(1, "on_f")
        self.os_f = Input(1, "os_f")
        self.eject_f = Input(1, "eject_f")
        self.oe_en = Output(1, "oe_en")
        self.ow_en = Output(1, "ow_en")
        self.on_en = Output(1, "on_en")
        self.os_en = Output(1, "os_en")
        self.Eject_en = Output(1, "Eject_en")

        with self.comb:
            self.oe_en <<= self.e_req & self.oe_f
            self.ow_en <<= self.w_req & self.ow_f
            self.on_en <<= self.n_req & self.on_f
            self.os_en <<= self.s_req & self.os_f
            self.Eject_en <<= self.eject_req & self.eject_f

print("  - ST defined")

# ---------------------------------------------------------------------------
# out_en_gen: output enable generator
# ---------------------------------------------------------------------------
class OutEnGen(Module):
    def __init__(self):
        super().__init__("out_en_gen")
        self.S_E = Input(3, "S_E")
        self.S_W = Input(3, "S_W")
        self.S_N = Input(3, "S_N")
        self.S_S = Input(3, "S_S")
        self.S_eject = Input(3, "S_eject")
        self.e_push_o = Input(1, "e_push_o")
        self.w_push_o = Input(1, "w_push_o")
        self.n_push_o = Input(1, "n_push_o")
        self.s_push_o = Input(1, "s_push_o")
        self.j_push_o = Input(1, "j_push_o")
        self.reset = Input(1, "reset")
        self.E_en = Output(1, "E_en")
        self.W_en = Output(1, "W_en")
        self.N_en = Output(1, "N_en")
        self.S_en = Output(1, "S_en")
        self.Eject_en = Output(1, "Eject_en")

        with self.comb:
            self.E_en <<= 0; self.W_en <<= 0; self.N_en <<= 0
            self.S_en <<= 0; self.Eject_en <<= 0
            with If(self.reset == 1):
                self.E_en <<= 0; self.W_en <<= 0; self.N_en <<= 0
                self.S_en <<= 0; self.Eject_en <<= 0
            with Else():
                with If(self.e_push_o == 1):
                    with If(self.S_E == 0): self.E_en <<= 1
                    with If(self.S_W == 0): self.W_en <<= 1
                    with If(self.S_N == 0): self.N_en <<= 1
                    with If(self.S_S == 0): self.S_en <<= 1
                    with If(self.S_eject == 0): self.Eject_en <<= 1
                with If(self.w_push_o == 1):
                    with If(self.S_E == 1): self.E_en <<= 1
                    with If(self.S_W == 1): self.W_en <<= 1
                    with If(self.S_N == 1): self.N_en <<= 1
                    with If(self.S_S == 1): self.S_en <<= 1
                    with If(self.S_eject == 1): self.Eject_en <<= 1
                with If(self.n_push_o == 1):
                    with If(self.S_E == 2): self.E_en <<= 1
                    with If(self.S_W == 2): self.W_en <<= 1
                    with If(self.S_N == 2): self.N_en <<= 1
                    with If(self.S_S == 2): self.S_en <<= 1
                    with If(self.S_eject == 2): self.Eject_en <<= 1
                with If(self.s_push_o == 1):
                    with If(self.S_E == 3): self.E_en <<= 1
                    with If(self.S_W == 3): self.W_en <<= 1
                    with If(self.S_N == 3): self.N_en <<= 1
                    with If(self.S_S == 3): self.S_en <<= 1
                    with If(self.S_eject == 3): self.Eject_en <<= 1
                with If(self.j_push_o == 1):
                    with If(self.S_E == 4): self.E_en <<= 1
                    with If(self.S_W == 4): self.W_en <<= 1
                    with If(self.S_N == 4): self.N_en <<= 1
                    with If(self.S_S == 4): self.S_en <<= 1
                    with If(self.S_eject == 4): self.Eject_en <<= 1

print("  - OutEnGen defined")


# ---------------------------------------------------------------------------
# Select_gen: crossbar select generator
# ---------------------------------------------------------------------------
class SelectGen(Module):
    def __init__(self):
        super().__init__("select_gen")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")
        self.e_g = Input(1, "e_g")
        self.w_g = Input(1, "w_g")
        self.n_g = Input(1, "n_g")
        self.s_g = Input(1, "s_g")
        self.inject_g = Input(1, "inject_g")
        self.e_req = Input(3, "e_req")
        self.w_req = Input(3, "w_req")
        self.n_req = Input(3, "n_req")
        self.s_req = Input(3, "s_req")
        self.inject_req = Input(3, "inject_req")
        self.s_e = Output(3, "s_e")
        self.s_w = Output(3, "s_w")
        self.s_n = Output(3, "s_n")
        self.s_s = Output(3, "s_s")
        self.s_eject = Output(3, "s_eject")

        self._s_e = Reg(3, "reg_s_e")
        self._s_w = Reg(3, "reg_s_w")
        self._s_n = Reg(3, "reg_s_n")
        self._s_s = Reg(3, "reg_s_s")
        self._s_eject = Reg(3, "reg_s_eject")

        with self.seq(self.clk, self.reset):
            with If(self.reset == 1):
                self._s_e <<= 7; self._s_w <<= 7; self._s_n <<= 7
                self._s_s <<= 7; self._s_eject <<= 7
            with Else():
                self._s_e <<= 7; self._s_w <<= 7; self._s_n <<= 7
                self._s_s <<= 7; self._s_eject <<= 7
                with If(self.e_g == 1):
                    with Switch(self.e_req) as sw:
                        with sw.case(0): self._s_e <<= 0
                        with sw.case(1): self._s_w <<= 0
                        with sw.case(2): self._s_n <<= 0
                        with sw.case(3): self._s_s <<= 0
                        with sw.case(4): self._s_eject <<= 0
                with If(self.w_g == 1):
                    with Switch(self.w_req) as sw:
                        with sw.case(0): self._s_e <<= 1
                        with sw.case(1): self._s_w <<= 1
                        with sw.case(2): self._s_n <<= 1
                        with sw.case(3): self._s_s <<= 1
                        with sw.case(4): self._s_eject <<= 1
                with If(self.n_g == 1):
                    with Switch(self.n_req) as sw:
                        with sw.case(0): self._s_e <<= 2
                        with sw.case(1): self._s_w <<= 2
                        with sw.case(2): self._s_n <<= 2
                        with sw.case(3): self._s_s <<= 2
                        with sw.case(4): self._s_eject <<= 2
                with If(self.s_g == 1):
                    with Switch(self.s_req) as sw:
                        with sw.case(0): self._s_e <<= 3
                        with sw.case(1): self._s_w <<= 3
                        with sw.case(2): self._s_n <<= 3
                        with sw.case(3): self._s_s <<= 3
                        with sw.case(4): self._s_eject <<= 3
                with If(self.inject_g == 1):
                    with Switch(self.inject_req) as sw:
                        with sw.case(0): self._s_e <<= 4
                        with sw.case(1): self._s_w <<= 4
                        with sw.case(2): self._s_n <<= 4
                        with sw.case(3): self._s_s <<= 4
                        with sw.case(4): self._s_eject <<= 4
        with self.comb:
            self.s_e <<= self._s_e; self.s_w <<= self._s_w; self.s_n <<= self._s_n
            self.s_s <<= self._s_s; self.s_eject <<= self._s_eject

print("  - SelectGen defined")

# ---------------------------------------------------------------------------
# set_Alloc: allocation setter
# ---------------------------------------------------------------------------
class SetAlloc(Module):
    def __init__(self):
        super().__init__("set_alloc")
        self.e_vc_grant = Input(1, "e_vc_grant")
        self.w_vc_grant = Input(1, "w_vc_grant")
        self.n_vc_grant = Input(1, "n_vc_grant")
        self.s_vc_grant = Input(1, "s_vc_grant")
        self.j_vc_grant = Input(1, "j_vc_grant")
        self.reset = Input(1, "reset")
        self.e_req = Input(3, "e_req")
        self.w_req = Input(3, "w_req")
        self.n_req = Input(3, "n_req")
        self.s_req = Input(3, "s_req")
        self.j_req = Input(3, "j_req")
        self.alloc_e = Output(1, "alloc_e")
        self.alloc_w = Output(1, "alloc_w")
        self.alloc_n = Output(1, "alloc_n")
        self.alloc_s = Output(1, "alloc_s")
        self.alloc_j = Output(1, "alloc_j")

        with self.comb:
            self.alloc_e <<= 0; self.alloc_w <<= 0; self.alloc_n <<= 0
            self.alloc_s <<= 0; self.alloc_j <<= 0
            with If(self.reset == 1):
                self.alloc_e <<= 0; self.alloc_w <<= 0; self.alloc_n <<= 0
                self.alloc_s <<= 0; self.alloc_j <<= 0
            with Else():
                with If(self.e_vc_grant == 1):
                    with Switch(self.e_req) as sw:
                        with sw.case(0): self.alloc_e <<= 1
                        with sw.case(1): self.alloc_w <<= 1
                        with sw.case(2): self.alloc_n <<= 1
                        with sw.case(3): self.alloc_s <<= 1
                        with sw.case(4): self.alloc_j <<= 1
                with If(self.w_vc_grant == 1):
                    with Switch(self.w_req) as sw:
                        with sw.case(0): self.alloc_e <<= 1
                        with sw.case(1): self.alloc_w <<= 1
                        with sw.case(2): self.alloc_n <<= 1
                        with sw.case(3): self.alloc_s <<= 1
                        with sw.case(4): self.alloc_j <<= 1
                with If(self.n_vc_grant == 1):
                    with Switch(self.n_req) as sw:
                        with sw.case(0): self.alloc_e <<= 1
                        with sw.case(1): self.alloc_w <<= 1
                        with sw.case(2): self.alloc_n <<= 1
                        with sw.case(3): self.alloc_s <<= 1
                        with sw.case(4): self.alloc_j <<= 1
                with If(self.s_vc_grant == 1):
                    with Switch(self.s_req) as sw:
                        with sw.case(0): self.alloc_e <<= 1
                        with sw.case(1): self.alloc_w <<= 1
                        with sw.case(2): self.alloc_n <<= 1
                        with sw.case(3): self.alloc_s <<= 1
                        with sw.case(4): self.alloc_j <<= 1
                with If(self.j_vc_grant == 1):
                    with Switch(self.j_req) as sw:
                        with sw.case(0): self.alloc_e <<= 1
                        with sw.case(1): self.alloc_w <<= 1
                        with sw.case(2): self.alloc_n <<= 1
                        with sw.case(3): self.alloc_s <<= 1
                        with sw.case(4): self.alloc_j <<= 1

print("  - SetAlloc defined")

# ---------------------------------------------------------------------------
# ST_Controler: Switch Traversal controller
# ---------------------------------------------------------------------------
class STControler(Module):
    def __init__(self):
        super().__init__("st_controler")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")
        self.e_vc_alloc = Input(1, "e_vc_alloc")
        self.w_vc_alloc = Input(1, "w_vc_alloc")
        self.n_vc_alloc = Input(1, "n_vc_alloc")
        self.s_vc_alloc = Input(1, "s_vc_alloc")
        self.inject_vc_alloc = Input(1, "inject_vc_alloc")
        self.oe_en = Input(1, "oe_en")
        self.ow_en = Input(1, "ow_en")
        self.on_en = Input(1, "on_en")
        self.os_en = Input(1, "os_en")
        self.Eject_en = Input(1, "Eject_en")
        self.e_out = Input(3, "e_out")
        self.w_out = Input(3, "w_out")
        self.n_out = Input(3, "n_out")
        self.s_out = Input(3, "s_out")
        self.inject_out = Input(3, "inject_out")
        self.e_ST_req = Output(1, "e_ST_req")
        self.w_ST_req = Output(1, "w_ST_req")
        self.n_ST_req = Output(1, "n_ST_req")
        self.s_ST_req = Output(1, "s_ST_req")
        self.eject_ST_req = Output(1, "eject_ST_req")
        self.e_ack = Output(1, "e_ack")
        self.w_ack = Output(1, "w_ack")
        self.n_ack = Output(1, "n_ack")
        self.s_ack = Output(1, "s_ack")
        self.inject_ack = Output(1, "inject_ack")

        with self.comb:
            er = Wire(1, "er"); wr = Wire(1, "wr"); nr = Wire(1, "nr")
            sr = Wire(1, "sr"); jr = Wire(1, "jr")
            ea = Wire(1, "ea"); wa = Wire(1, "wa"); na = Wire(1, "na")
            sa = Wire(1, "sa"); ja = Wire(1, "ja")
            er <<= 0; wr <<= 0; nr <<= 0; sr <<= 0; jr <<= 0
            ea <<= 0; wa <<= 0; na <<= 0; sa <<= 0; ja <<= 0

            with If(self.reset == 1):
                er <<= 0; wr <<= 0; nr <<= 0; sr <<= 0; jr <<= 0
            with Else():
                with If(self.e_vc_alloc == 1 and self.oe_en == 1):
                    with Switch(self.e_out) as sw:
                        with sw.case(0): er <<= 1
                        with sw.case(1): wr <<= 1
                        with sw.case(2): nr <<= 1
                        with sw.case(3): sr <<= 1
                        with sw.case(4): jr <<= 1
                with If(self.w_vc_alloc == 1 and self.ow_en == 1):
                    with Switch(self.w_out) as sw:
                        with sw.case(0): er <<= 1
                        with sw.case(1): wr <<= 1
                        with sw.case(2): nr <<= 1
                        with sw.case(3): sr <<= 1
                        with sw.case(4): jr <<= 1
                with If(self.n_vc_alloc == 1 and self.on_en == 1):
                    with Switch(self.n_out) as sw:
                        with sw.case(0): er <<= 1
                        with sw.case(1): wr <<= 1
                        with sw.case(2): nr <<= 1
                        with sw.case(3): sr <<= 1
                        with sw.case(4): jr <<= 1
                with If(self.s_vc_alloc == 1 and self.os_en == 1):
                    with Switch(self.s_out) as sw:
                        with sw.case(0): er <<= 1
                        with sw.case(1): wr <<= 1
                        with sw.case(2): nr <<= 1
                        with sw.case(3): sr <<= 1
                        with sw.case(4): jr <<= 1
                with If(self.inject_vc_alloc == 1 and self.Eject_en == 1):
                    with Switch(self.inject_out) as sw:
                        with sw.case(0): er <<= 1
                        with sw.case(1): wr <<= 1
                        with sw.case(2): nr <<= 1
                        with sw.case(3): sr <<= 1
                        with sw.case(4): jr <<= 1

                # ack generation: if a port's request is granted by any input
                ea <<= self.e_vc_alloc & self.oe_en
                wa <<= self.w_vc_alloc & self.ow_en
                na <<= self.n_vc_alloc & self.on_en
                sa <<= self.s_vc_alloc & self.os_en
                ja <<= self.inject_vc_alloc & self.Eject_en

            self.e_ST_req <<= er; self.w_ST_req <<= wr; self.n_ST_req <<= nr
            self.s_ST_req <<= sr; self.eject_ST_req <<= jr
            self.e_ack <<= ea; self.w_ack <<= wa; self.n_ack <<= na
            self.s_ack <<= sa; self.inject_ack <<= ja

print("  - STControler defined")

# ---------------------------------------------------------------------------
# VC_Alloc: Virtual Channel Allocator (round-robin via Counter)
# ---------------------------------------------------------------------------
class VCAlloc(Module):
    def __init__(self):
        super().__init__("vc_alloc")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")
        self.E_req = Input(3, "E_req")
        self.W_req = Input(3, "W_req")
        self.N_req = Input(3, "N_req")
        self.S_req = Input(3, "S_req")
        self.Inject_req = Input(3, "Inject_req")
        self.oe_en = Input(1, "oe_en")
        self.ow_en = Input(1, "ow_en")
        self.on_en = Input(1, "on_en")
        self.os_en = Input(1, "os_en")
        self.eject_en = Input(1, "eject_en")
        self.ie_en = Input(1, "ie_en")
        self.iw_en = Input(1, "iw_en")
        self.in_en = Input(1, "in_en")
        self.is_en = Input(1, "is_en")
        self.inject_en = Input(1, "inject_en")
        self.vc_e_f = Input(1, "vc_e_f")
        self.vc_w_f = Input(1, "vc_w_f")
        self.vc_n_f = Input(1, "vc_n_f")
        self.vc_s_f = Input(1, "vc_s_f")
        self.vc_j_f = Input(1, "vc_j_f")
        self.vc_g_e = Output(1, "vc_g_e")
        self.vc_g_w = Output(1, "vc_g_w")
        self.vc_g_n = Output(1, "vc_g_n")
        self.vc_g_s = Output(1, "vc_g_s")
        self.vc_g_injec = Output(1, "vc_g_injec")

        self._vc_g_e = Reg(1, "reg_vc_g_e")
        self._vc_g_w = Reg(1, "reg_vc_g_w")
        self._vc_g_n = Reg(1, "reg_vc_g_n")
        self._vc_g_s = Reg(1, "reg_vc_g_s")
        self._vc_g_injec = Reg(1, "reg_vc_g_injec")

        # Counters for round-robin arbitration
        self._en_c_e = Reg(1, "en_c_e")
        self._en_c_w = Reg(1, "en_c_w")
        self._en_c_n = Reg(1, "en_c_n")
        self._en_c_s = Reg(1, "en_c_s")
        self._en_c_j = Reg(1, "en_c_j")

        self._cnt_e = Counter()
        self._cnt_w = Counter()
        self._cnt_n = Counter()
        self._cnt_s = Counter()
        self._cnt_j = Counter()

        # Instantiate counters
        w_count_e = Wire(3, "w_count_e")
        w_count_w = Wire(3, "w_count_w")
        w_count_n = Wire(3, "w_count_n")
        w_count_s = Wire(3, "w_count_s")
        w_count_j = Wire(3, "w_count_j")

        self.instantiate(self._cnt_e, "c_e", port_map={
            "clk": self.clk, "reset": self.reset, "en": self._en_c_e, "c": w_count_e,
        })
        self.instantiate(self._cnt_w, "c_w", port_map={
            "clk": self.clk, "reset": self.reset, "en": self._en_c_w, "c": w_count_w,
        })
        self.instantiate(self._cnt_n, "c_n", port_map={
            "clk": self.clk, "reset": self.reset, "en": self._en_c_n, "c": w_count_n,
        })
        self.instantiate(self._cnt_s, "c_s", port_map={
            "clk": self.clk, "reset": self.reset, "en": self._en_c_s, "c": w_count_s,
        })
        self.instantiate(self._cnt_j, "c_j", port_map={
            "clk": self.clk, "reset": self.reset, "en": self._en_c_j, "c": w_count_j,
        })

        with self.seq(self.clk, self.reset):
            with If(self.reset == 1):
                self._vc_g_e <<= 0; self._vc_g_w <<= 0; self._vc_g_n <<= 0
                self._vc_g_s <<= 0; self._vc_g_injec <<= 0
                self._en_c_e <<= 1; self._en_c_w <<= 1; self._en_c_n <<= 1
                self._en_c_s <<= 1; self._en_c_j <<= 1
            with Else():
                # Default: enable all counters
                self._en_c_e <<= 1; self._en_c_w <<= 1; self._en_c_n <<= 1
                self._en_c_s <<= 1; self._en_c_j <<= 1

                # East output arbitration
                with If(self.vc_e_f == 1):
                    with If(self._vc_g_e == 1):
                        self._vc_g_e <<= 0
                        with Switch(self.E_req) as sw:
                            with sw.case(0): self._en_c_e <<= 0
                            with sw.case(1): self._en_c_w <<= 0
                            with sw.case(2): self._en_c_n <<= 0
                            with sw.case(3): self._en_c_s <<= 0
                            with sw.case(4): self._en_c_j <<= 0
                with Else():
                    with If(self.oe_en == 1):
                        self._vc_g_e <<= 1

                # West output arbitration
                with If(self.vc_w_f == 1):
                    with If(self._vc_g_w == 1):
                        self._vc_g_w <<= 0
                        with Switch(self.W_req) as sw:
                            with sw.case(0): self._en_c_e <<= 0
                            with sw.case(1): self._en_c_w <<= 0
                            with sw.case(2): self._en_c_n <<= 0
                            with sw.case(3): self._en_c_s <<= 0
                            with sw.case(4): self._en_c_j <<= 0
                with Else():
                    with If(self.ow_en == 1):
                        self._vc_g_w <<= 1

                # North output arbitration
                with If(self.vc_n_f == 1):
                    with If(self._vc_g_n == 1):
                        self._vc_g_n <<= 0
                        with Switch(self.N_req) as sw:
                            with sw.case(0): self._en_c_e <<= 0
                            with sw.case(1): self._en_c_w <<= 0
                            with sw.case(2): self._en_c_n <<= 0
                            with sw.case(3): self._en_c_s <<= 0
                            with sw.case(4): self._en_c_j <<= 0
                with Else():
                    with If(self.on_en == 1):
                        self._vc_g_n <<= 1

                # South output arbitration
                with If(self.vc_s_f == 1):
                    with If(self._vc_g_s == 1):
                        self._vc_g_s <<= 0
                        with Switch(self.S_req) as sw:
                            with sw.case(0): self._en_c_e <<= 0
                            with sw.case(1): self._en_c_w <<= 0
                            with sw.case(2): self._en_c_n <<= 0
                            with sw.case(3): self._en_c_s <<= 0
                            with sw.case(4): self._en_c_j <<= 0
                with Else():
                    with If(self.os_en == 1):
                        self._vc_g_s <<= 1

                # Eject output arbitration
                with If(self.vc_j_f == 1):
                    with If(self._vc_g_injec == 1):
                        self._vc_g_injec <<= 0
                        with Switch(self.Inject_req) as sw:
                            with sw.case(0): self._en_c_e <<= 0
                            with sw.case(1): self._en_c_w <<= 0
                            with sw.case(2): self._en_c_n <<= 0
                            with sw.case(3): self._en_c_s <<= 0
                            with sw.case(4): self._en_c_j <<= 0
                with Else():
                    with If(self.eject_en == 1):
                        self._vc_g_injec <<= 1

        with self.comb:
            self.vc_g_e <<= self._vc_g_e; self.vc_g_w <<= self._vc_g_w
            self.vc_g_n <<= self._vc_g_n; self.vc_g_s <<= self._vc_g_s
            self.vc_g_injec <<= self._vc_g_injec

print("  - VCAlloc defined")


# ---------------------------------------------------------------------------
# input_Unit: input processing unit (Buffer + Route_Func + FSM)
# ---------------------------------------------------------------------------
class InputUnit(Module):
    def __init__(self):
        super().__init__("input_unit")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")
        self.push_x = Input(1, "push_x")
        self.PW_fail = Input(1, "PW_fail")
        self.vc_grant = Input(1, "vc_grant")
        self.ST_ack = Input(1, "ST_ack")
        self.bf_in = Input(FLIT_WIDTH, "bf_in")
        self.X_cur = Input(X_WIDTH, "X_cur")
        self.Y_cur = Input(Y_WIDTH, "Y_cur")
        self.in_channel = Input(3, "in_channel")
        self.bf_out = Output(FLIT_WIDTH, "bf_out")
        self.en = Output(1, "en")
        self.em_pl = Output(3, "em_pl")
        self.out_num = Output(3, "out_num")
        self.PW = Output(1, "PW")
        self.vc_g = Output(1, "vc_g")
        self.vc_f = Output(1, "vc_f")
        self.push_o = Output(1, "push_o")
        self.push_ack = Output(1, "push_ack")

        # Internal buffer
        self._buf = Buffer()
        w_buf_out = Wire(FLIT_WIDTH, "w_buf_out")
        w_em_pl = Wire(3, "w_em_pl")
        self.instantiate(self._buf, "bf", port_map={
            "clk": self.clk, "reset": self.reset,
            "pop": Wire(1, "w_pop"), "push": Wire(1, "w_push"),
            "bf_in": self.bf_in, "bf_out": w_buf_out, "em_pl": w_em_pl,
        })

        # Route function
        self._rf = RouteFunc()
        w_valid_out = Wire(5, "w_valid_out")
        w_status = Wire(5, "w_status")
        self.instantiate(self._rf, "rf", port_map={
            "X_cur": self.X_cur, "Y_cur": self.Y_cur,
            "X_dest": Wire(X_WIDTH, "w_X_dest"),
            "Y_dest": Wire(Y_WIDTH, "w_Y_dest"),
            "reset": self.reset,
            "valid_out": w_valid_out, "status": w_status,
        })

        # FSM state
        self._state = Reg(3, "state")
        self._next_state = Wire(3, "next_state")

        # Internal registers
        self._X_dest = Reg(X_WIDTH, "X_dest")
        self._Y_dest = Reg(Y_WIDTH, "Y_dest")
        self._Pri = Reg(1, "Pri")
        self._pop = Reg(1, "pop_r")
        self._push = Reg(1, "push_r")

        with self.seq(self.clk, self.reset):
            with If(self.reset == 1):
                self._state <<= 0
                self._X_dest <<= 0; self._Y_dest <<= 0
                self._Pri <<= 0; self._pop <<= 0; self._push <<= 0
            with Else():
                self._state <<= self._next_state
                with If(self.push_x == 1 and w_em_pl > 0):
                    self._X_dest <<= self.bf_in[55:53]
                    self._Y_dest <<= self.bf_in[52:50]

        # FSM next_state logic
        with self.comb:
            self._next_state <<= self._state
            with Switch(self._state) as sw:
                with sw.case(0):
                    with If(self.vc_grant == 0):
                        self._next_state <<= 0
                    with Else():
                        self._next_state <<= 1
                with sw.case(1):
                    with If(self.ST_ack):
                        self._next_state <<= 2
                    with Else():
                        self._next_state <<= 1
                with sw.case(2): self._next_state <<= 3
                with sw.case(3): self._next_state <<= 4
                with sw.case(4): self._next_state <<= 5
                with sw.case(5): self._next_state <<= 6
                with sw.case(6): self._next_state <<= 0

            # Route func inputs
            w_X_dest = Wire(X_WIDTH, "w_X_dest")
            w_Y_dest = Wire(Y_WIDTH, "w_Y_dest")
            w_X_dest <<= self._X_dest
            w_Y_dest <<= self._Y_dest
            # Connect to route func (via comb override - in real design these would be wires)
            # For simplicity, we connect them directly in instantiate above

            # Output logic
            self.bf_out <<= w_buf_out
            self.em_pl <<= w_em_pl
            self.en <<= (self._state != 0)
            self.out_num <<= self._X_dest  # simplified
            self.PW <<= (self._state == 1)
            self.vc_g <<= self.vc_grant
            self.vc_f <<= (self._state == 0)  # simplified
            self.push_o <<= (self._state >= 2) & (self._state <= 6)
            self.push_ack <<= (self.push_x == 1) & (w_em_pl > 0)

            # Buffer control
            w_pop = Wire(1, "w_pop")
            w_push = Wire(1, "w_push")
            w_pop <<= (self._state == 6)  # pop at end of transmission
            w_push <<= self.push_x & (w_em_pl > 0)

print("  - InputUnit defined")

# ---------------------------------------------------------------------------
# output_unit: output processing unit (Buffer + write_req logic)
# ---------------------------------------------------------------------------
class OutputUnit(Module):
    def __init__(self):
        super().__init__("output_unit")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")
        self.push = Input(1, "push")
        self.next_router_state = Input(1, "next_router_state")
        self.alloc = Input(1, "alloc")
        self.bf_in = Input(FLIT_WIDTH, "bf_in")
        self.write_req_ack = Input(1, "write_req_ack")
        self.bf_out = Output(FLIT_WIDTH, "bf_out")
        self.write_req = Output(1, "write_req")
        self.allocOrnot = Output(1, "allocOrnot")
        self.em_pl = Output(3, "em_pl")

        # Internal buffer
        self._buf = Buffer()
        w_buf_out = Wire(FLIT_WIDTH, "w_buf_out")
        w_em_pl = Wire(3, "w_em_pl")
        w_pop = Wire(1, "w_pop")
        w_push_x = Wire(1, "w_push_x")
        self.instantiate(self._buf, "bf", port_map={
            "clk": self.clk, "reset": self.reset,
            "pop": w_pop, "push": w_push_x,
            "bf_in": self.bf_in, "bf_out": w_buf_out, "em_pl": w_em_pl,
        })

        with self.comb:
            # Default assignments at top (prevents latch_risk warnings)
            self.write_req <<= 0
            w_push_x <<= self.push
            w_pop <<= self.write_req_ack
            self.bf_out <<= w_buf_out
            self.em_pl <<= w_em_pl

            # push_x logic: if push==0 and em_pl>0 and tail flit detected, force push
            with If(self.push == 0 and w_em_pl > 0 and self.bf_in[63:62] == 2):
                with If(w_buf_out[63:62] == 1 or w_buf_out[63:62] == 3):
                    w_push_x <<= 1

            # write_req: next router available and buffer has data
            with If(self.reset == 1):
                self.write_req <<= 0
            with Else():
                with If(self.next_router_state == 1 and w_buf_out[63:62] != 0 and w_em_pl != 4):
                    self.write_req <<= 1

            # allocOrnot
            with If(self.reset == 1):
                self.allocOrnot <<= 0
            with Else():
                self.allocOrnot <<= self.alloc

print("  - OutputUnit defined")

# ---------------------------------------------------------------------------
# Router: 5-port router
# ---------------------------------------------------------------------------
class Router(Module):
    def __init__(self):
        super().__init__("router")
        self.X_cur = Input(X_WIDTH, "X_cur")
        self.Y_cur = Input(Y_WIDTH, "Y_cur")
        self.ie = Input(FLIT_WIDTH, "ie")
        self.iw = Input(FLIT_WIDTH, "iw")
        self.in_ = Input(FLIT_WIDTH, "in_")
        self.is_ = Input(FLIT_WIDTH, "is_")
        self.inject = Input(FLIT_WIDTH, "inject")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")
        self.push_e = Input(1, "push_e")
        self.push_w = Input(1, "push_w")
        self.push_n = Input(1, "push_n")
        self.push_s = Input(1, "push_s")
        self.push_j = Input(1, "push_j")
        self.e_state = Input(1, "e_state")
        self.w_state = Input(1, "w_state")
        self.n_state = Input(1, "n_state")
        self.s_state = Input(1, "s_state")
        self.eject_state = Input(1, "eject_state")
        self.oe = Output(FLIT_WIDTH, "oe")
        self.ow = Output(FLIT_WIDTH, "ow")
        self.on_ = Output(FLIT_WIDTH, "on_")
        self.os_ = Output(FLIT_WIDTH, "os_")
        self.eject = Output(FLIT_WIDTH, "eject")
        self.write_req_e = Output(1, "write_req_e")
        self.write_req_w = Output(1, "write_req_w")
        self.write_req_n = Output(1, "write_req_n")
        self.write_req_s = Output(1, "write_req_s")
        self.write_req_j = Output(1, "write_req_j")
        self.e_e = Output(1, "e_e")
        self.w_e = Output(1, "w_e")
        self.n_e = Output(1, "n_e")
        self.s_e = Output(1, "s_e")
        self.j_e = Output(1, "j_e")
        self.w_e_ack = Input(1, "w_e_ack")
        self.w_w_ack = Input(1, "w_w_ack")
        self.w_n_ack = Input(1, "w_n_ack")
        self.w_s_ack = Input(1, "w_s_ack")
        self.w_j_ack = Input(1, "w_j_ack")
        self.push_e_ack = Output(1, "push_e_ack")
        self.push_w_ack = Output(1, "push_w_ack")
        self.push_n_ack = Output(1, "push_n_ack")
        self.push_s_ack = Output(1, "push_s_ack")
        self.push_j_ack = Output(1, "push_j_ack")

        # Input units (5 ports)
        self._iu_e = InputUnit()
        self._iu_w = InputUnit()
        self._iu_n = InputUnit()
        self._iu_s = InputUnit()
        self._iu_j = InputUnit()

        # Output units (5 ports)
        self._ou_e = OutputUnit()
        self._ou_w = OutputUnit()
        self._ou_n = OutputUnit()
        self._ou_s = OutputUnit()
        self._ou_j = OutputUnit()

        # Internal wires for input units
        w_iu_e_out = Wire(FLIT_WIDTH, "w_iu_e_out")
        w_iu_w_out = Wire(FLIT_WIDTH, "w_iu_w_out")
        w_iu_n_out = Wire(FLIT_WIDTH, "w_iu_n_out")
        w_iu_s_out = Wire(FLIT_WIDTH, "w_iu_s_out")
        w_iu_j_out = Wire(FLIT_WIDTH, "w_iu_j_out")
        w_iu_e_en = Wire(1, "w_iu_e_en")
        w_iu_w_en = Wire(1, "w_iu_w_en")
        w_iu_n_en = Wire(1, "w_iu_n_en")
        w_iu_s_en = Wire(1, "w_iu_s_en")
        w_iu_j_en = Wire(1, "w_iu_j_en")
        w_iu_e_em = Wire(3, "w_iu_e_em")
        w_iu_w_em = Wire(3, "w_iu_w_em")
        w_iu_n_em = Wire(3, "w_iu_n_em")
        w_iu_s_em = Wire(3, "w_iu_s_em")
        w_iu_j_em = Wire(3, "w_iu_j_em")
        w_iu_e_on = Wire(3, "w_iu_e_on")
        w_iu_w_on = Wire(3, "w_iu_w_on")
        w_iu_n_on = Wire(3, "w_iu_n_on")
        w_iu_s_on = Wire(3, "w_iu_s_on")
        w_iu_j_on = Wire(3, "w_iu_j_on")
        w_iu_e_pw = Wire(1, "w_iu_e_pw")
        w_iu_w_pw = Wire(1, "w_iu_w_pw")
        w_iu_n_pw = Wire(1, "w_iu_n_pw")
        w_iu_s_pw = Wire(1, "w_iu_s_pw")
        w_iu_j_pw = Wire(1, "w_iu_j_pw")
        w_iu_e_vg = Wire(1, "w_iu_e_vg")
        w_iu_w_vg = Wire(1, "w_iu_w_vg")
        w_iu_n_vg = Wire(1, "w_iu_n_vg")
        w_iu_s_vg = Wire(1, "w_iu_s_vg")
        w_iu_j_vg = Wire(1, "w_iu_j_vg")
        w_iu_e_vf = Wire(1, "w_iu_e_vf")
        w_iu_w_vf = Wire(1, "w_iu_w_vf")
        w_iu_n_vf = Wire(1, "w_iu_n_vf")
        w_iu_s_vf = Wire(1, "w_iu_s_vf")
        w_iu_j_vf = Wire(1, "w_iu_j_vf")
        w_iu_e_po = Wire(1, "w_iu_e_po")
        w_iu_w_po = Wire(1, "w_iu_w_po")
        w_iu_n_po = Wire(1, "w_iu_n_po")
        w_iu_s_po = Wire(1, "w_iu_s_po")
        w_iu_j_po = Wire(1, "w_iu_j_po")

        # Instantiate input units
        self.instantiate(self._iu_e, "iu_e", port_map={
            "clk": self.clk, "reset": self.reset,
            "push_x": self.push_e, "PW_fail": 0, "vc_grant": w_iu_e_vg,
            "ST_ack": 0, "bf_in": self.ie, "X_cur": self.X_cur, "Y_cur": self.Y_cur,
            "in_channel": Const(0, 3),
            "bf_out": w_iu_e_out, "en": w_iu_e_en, "em_pl": w_iu_e_em,
            "out_num": w_iu_e_on, "PW": w_iu_e_pw, "vc_g": w_iu_e_vg,
            "vc_f": w_iu_e_vf, "push_o": w_iu_e_po, "push_ack": self.push_e_ack,
        })
        self.instantiate(self._iu_w, "iu_w", port_map={
            "clk": self.clk, "reset": self.reset,
            "push_x": self.push_w, "PW_fail": 0, "vc_grant": w_iu_w_vg,
            "ST_ack": 0, "bf_in": self.iw, "X_cur": self.X_cur, "Y_cur": self.Y_cur,
            "in_channel": Const(1, 3),
            "bf_out": w_iu_w_out, "en": w_iu_w_en, "em_pl": w_iu_w_em,
            "out_num": w_iu_w_on, "PW": w_iu_w_pw, "vc_g": w_iu_w_vg,
            "vc_f": w_iu_w_vf, "push_o": w_iu_w_po, "push_ack": self.push_w_ack,
        })
        self.instantiate(self._iu_n, "iu_n", port_map={
            "clk": self.clk, "reset": self.reset,
            "push_x": self.push_n, "PW_fail": 0, "vc_grant": w_iu_n_vg,
            "ST_ack": 0, "bf_in": self.in_, "X_cur": self.X_cur, "Y_cur": self.Y_cur,
            "in_channel": Const(2, 3),
            "bf_out": w_iu_n_out, "en": w_iu_n_en, "em_pl": w_iu_n_em,
            "out_num": w_iu_n_on, "PW": w_iu_n_pw, "vc_g": w_iu_n_vg,
            "vc_f": w_iu_n_vf, "push_o": w_iu_n_po, "push_ack": self.push_n_ack,
        })
        self.instantiate(self._iu_s, "iu_s", port_map={
            "clk": self.clk, "reset": self.reset,
            "push_x": self.push_s, "PW_fail": 0, "vc_grant": w_iu_s_vg,
            "ST_ack": 0, "bf_in": self.is_, "X_cur": self.X_cur, "Y_cur": self.Y_cur,
            "in_channel": Const(3, 3),
            "bf_out": w_iu_s_out, "en": w_iu_s_en, "em_pl": w_iu_s_em,
            "out_num": w_iu_s_on, "PW": w_iu_s_pw, "vc_g": w_iu_s_vg,
            "vc_f": w_iu_s_vf, "push_o": w_iu_s_po, "push_ack": self.push_s_ack,
        })
        self.instantiate(self._iu_j, "iu_j", port_map={
            "clk": self.clk, "reset": self.reset,
            "push_x": self.push_j, "PW_fail": 0, "vc_grant": w_iu_j_vg,
            "ST_ack": 0, "bf_in": self.inject, "X_cur": self.X_cur, "Y_cur": self.Y_cur,
            "in_channel": Const(4, 3),
            "bf_out": w_iu_j_out, "en": w_iu_j_en, "em_pl": w_iu_j_em,
            "out_num": w_iu_j_on, "PW": w_iu_j_pw, "vc_g": w_iu_j_vg,
            "vc_f": w_iu_j_vf, "push_o": w_iu_j_po, "push_ack": self.push_j_ack,
        })

        # Internal wires for output units
        w_ou_e_out = Wire(FLIT_WIDTH, "w_ou_e_out")
        w_ou_w_out = Wire(FLIT_WIDTH, "w_ou_w_out")
        w_ou_n_out = Wire(FLIT_WIDTH, "w_ou_n_out")
        w_ou_s_out = Wire(FLIT_WIDTH, "w_ou_s_out")
        w_ou_j_out = Wire(FLIT_WIDTH, "w_ou_j_out")
        w_ou_e_wr = Wire(1, "w_ou_e_wr")
        w_ou_w_wr = Wire(1, "w_ou_w_wr")
        w_ou_n_wr = Wire(1, "w_ou_n_wr")
        w_ou_s_wr = Wire(1, "w_ou_s_wr")
        w_ou_j_wr = Wire(1, "w_ou_j_wr")
        w_ou_e_al = Wire(1, "w_ou_e_al")
        w_ou_w_al = Wire(1, "w_ou_w_al")
        w_ou_n_al = Wire(1, "w_ou_n_al")
        w_ou_s_al = Wire(1, "w_ou_s_al")
        w_ou_j_al = Wire(1, "w_ou_j_al")
        w_ou_e_em = Wire(3, "w_ou_e_em")
        w_ou_w_em = Wire(3, "w_ou_w_em")
        w_ou_n_em = Wire(3, "w_ou_n_em")
        w_ou_s_em = Wire(3, "w_ou_s_em")
        w_ou_j_em = Wire(3, "w_ou_j_em")

        # Instantiate output units
        self.instantiate(self._ou_e, "ou_e", port_map={
            "clk": self.clk, "reset": self.reset,
            "push": w_iu_e_po, "next_router_state": self.e_state,
            "alloc": w_ou_e_al, "bf_in": w_iu_e_out,
            "write_req_ack": self.w_e_ack,
            "bf_out": w_ou_e_out, "write_req": w_ou_e_wr,
            "allocOrnot": w_ou_e_al, "em_pl": w_ou_e_em,
        })
        self.instantiate(self._ou_w, "ou_w", port_map={
            "clk": self.clk, "reset": self.reset,
            "push": w_iu_w_po, "next_router_state": self.w_state,
            "alloc": w_ou_w_al, "bf_in": w_iu_w_out,
            "write_req_ack": self.w_w_ack,
            "bf_out": w_ou_w_out, "write_req": w_ou_w_wr,
            "allocOrnot": w_ou_w_al, "em_pl": w_ou_w_em,
        })
        self.instantiate(self._ou_n, "ou_n", port_map={
            "clk": self.clk, "reset": self.reset,
            "push": w_iu_n_po, "next_router_state": self.n_state,
            "alloc": w_ou_n_al, "bf_in": w_iu_n_out,
            "write_req_ack": self.w_n_ack,
            "bf_out": w_ou_n_out, "write_req": w_ou_n_wr,
            "allocOrnot": w_ou_n_al, "em_pl": w_ou_n_em,
        })
        self.instantiate(self._ou_s, "ou_s", port_map={
            "clk": self.clk, "reset": self.reset,
            "push": w_iu_s_po, "next_router_state": self.s_state,
            "alloc": w_ou_s_al, "bf_in": w_iu_s_out,
            "write_req_ack": self.w_s_ack,
            "bf_out": w_ou_s_out, "write_req": w_ou_s_wr,
            "allocOrnot": w_ou_s_al, "em_pl": w_ou_s_em,
        })
        self.instantiate(self._ou_j, "ou_j", port_map={
            "clk": self.clk, "reset": self.reset,
            "push": w_iu_j_po, "next_router_state": self.eject_state,
            "alloc": w_ou_j_al, "bf_in": w_iu_j_out,
            "write_req_ack": self.w_j_ack,
            "bf_out": w_ou_j_out, "write_req": w_ou_j_wr,
            "allocOrnot": w_ou_j_al, "em_pl": w_ou_j_em,
        })

        # CrossBar
        self._cb = CrossBar()
        w_cb_oe = Wire(FLIT_WIDTH, "w_cb_oe")
        w_cb_ow = Wire(FLIT_WIDTH, "w_cb_ow")
        w_cb_on = Wire(FLIT_WIDTH, "w_cb_on")
        w_cb_os = Wire(FLIT_WIDTH, "w_cb_os")
        w_cb_ej = Wire(FLIT_WIDTH, "w_cb_ej")
        self.instantiate(self._cb, "cb", port_map={
            "S_E": w_iu_e_on, "S_W": w_iu_w_on, "S_N": w_iu_n_on,
            "S_S": w_iu_s_on, "S_Ejec": w_iu_j_on,
            "IE": w_iu_e_out, "IW": w_iu_w_out, "IN": w_iu_n_out,
            "IS": w_iu_s_out, "Inject": w_iu_j_out,
            "OE": w_cb_oe, "OW": w_cb_ow, "ON": w_cb_on,
            "OS": w_cb_os, "Eject": w_cb_ej,
        })

        # Output flags (registered)
        self._oe_f = Reg(1, "oe_f")
        self._ow_f = Reg(1, "ow_f")
        self._on_f = Reg(1, "on_f")
        self._os_f = Reg(1, "os_f")
        self._eject_f = Reg(1, "eject_f")

        with self.seq(self.clk, self.reset):
            with If(self.reset == 1):
                self._oe_f <<= 0; self._ow_f <<= 0; self._on_f <<= 0
                self._os_f <<= 0; self._eject_f <<= 0
            with Else():
                self._oe_f <<= w_ou_e_em > 0
                self._ow_f <<= w_ou_w_em > 0
                self._on_f <<= w_ou_n_em > 0
                self._os_f <<= w_ou_s_em > 0
                self._eject_f <<= w_ou_j_em > 0

        # Output assignments
        with self.comb:
            self.oe <<= w_cb_oe; self.ow <<= w_cb_ow; self.on_ <<= w_cb_on
            self.os_ <<= w_cb_os; self.eject <<= w_cb_ej
            self.write_req_e <<= w_ou_e_wr; self.write_req_w <<= w_ou_w_wr
            self.write_req_n <<= w_ou_n_wr; self.write_req_s <<= w_ou_s_wr
            self.write_req_j <<= w_ou_j_wr
            self.e_e <<= w_ou_e_em > 0; self.w_e <<= w_ou_w_em > 0
            self.n_e <<= w_ou_n_em > 0; self.s_e <<= w_ou_s_em > 0
            self.j_e <<= w_ou_j_em > 0

print("  - Router defined")

# ---------------------------------------------------------------------------
# Process_Node: router + inject/eject interface
# ---------------------------------------------------------------------------
class ProcessNode(Module):
    def __init__(self):
        super().__init__("process_node")
        self.X_cur = Input(X_WIDTH, "X_cur")
        self.Y_cur = Input(Y_WIDTH, "Y_cur")
        self.ie = Input(FLIT_WIDTH, "ie")
        self.iw = Input(FLIT_WIDTH, "iw")
        self.in_ = Input(FLIT_WIDTH, "in_")
        self.is_ = Input(FLIT_WIDTH, "is_")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")
        self.push_e = Input(1, "push_e")
        self.push_w = Input(1, "push_w")
        self.push_n = Input(1, "push_n")
        self.push_s = Input(1, "push_s")
        self.e_state = Input(1, "e_state")
        self.w_state = Input(1, "w_state")
        self.n_state = Input(1, "n_state")
        self.s_state = Input(1, "s_state")
        self.oe = Output(FLIT_WIDTH, "oe")
        self.ow = Output(FLIT_WIDTH, "ow")
        self.on_ = Output(FLIT_WIDTH, "on_")
        self.os_ = Output(FLIT_WIDTH, "os_")
        self.write_req_e = Output(1, "write_req_e")
        self.write_req_w = Output(1, "write_req_w")
        self.write_req_n = Output(1, "write_req_n")
        self.write_req_s = Output(1, "write_req_s")
        self.e_e = Output(1, "e_e")
        self.w_e = Output(1, "w_e")
        self.n_e = Output(1, "n_e")
        self.s_e = Output(1, "s_e")
        self.w_e_ack = Input(1, "w_e_ack")
        self.w_w_ack = Input(1, "w_w_ack")
        self.w_n_ack = Input(1, "w_n_ack")
        self.w_s_ack = Input(1, "w_s_ack")
        self.push_e_ack = Output(1, "push_e_ack")
        self.push_w_ack = Output(1, "push_w_ack")
        self.push_n_ack = Output(1, "push_n_ack")
        self.push_s_ack = Output(1, "push_s_ack")
        self.inject = Input(FLIT_WIDTH, "inject")
        self.push_j = Input(1, "push_j")
        self.w_j_ack = Input(1, "w_j_ack")
        self.write_req_j = Output(1, "write_req_j")
        self.j_e = Output(1, "j_e")
        self.push_j_ack = Output(1, "push_j_ack")
        self.eject = Output(FLIT_WIDTH, "eject")

        self._router = Router()
        self.instantiate(self._router, "R", port_map={
            "X_cur": self.X_cur, "Y_cur": self.Y_cur,
            "ie": self.ie, "iw": self.iw, "in_": self.in_, "is_": self.is_,
            "inject": self.inject, "clk": self.clk, "reset": self.reset,
            "push_e": self.push_e, "push_w": self.push_w,
            "push_n": self.push_n, "push_s": self.push_s, "push_j": self.push_j,
            "e_state": self.e_state, "w_state": self.w_state,
            "n_state": self.n_state, "s_state": self.s_state,
            "eject_state": Const(1, 1),
            "oe": self.oe, "ow": self.ow, "on_": self.on_, "os_": self.os_,
            "eject": self.eject,
            "write_req_e": self.write_req_e, "write_req_w": self.write_req_w,
            "write_req_n": self.write_req_n, "write_req_s": self.write_req_s,
            "write_req_j": self.write_req_j,
            "e_e": self.e_e, "w_e": self.w_e, "n_e": self.n_e, "s_e": self.s_e,
            "j_e": self.j_e,
            "w_e_ack": self.w_e_ack, "w_w_ack": self.w_w_ack,
            "w_n_ack": self.w_n_ack, "w_s_ack": self.w_s_ack, "w_j_ack": self.w_j_ack,
            "push_e_ack": self.push_e_ack, "push_w_ack": self.push_w_ack,
            "push_n_ack": self.push_n_ack, "push_s_ack": self.push_s_ack,
            "push_j_ack": self.push_j_ack,
        })

print("  - ProcessNode defined")

# ---------------------------------------------------------------------------
# Network: 8x8 mesh
# ---------------------------------------------------------------------------
class Network(Module):
    def __init__(self):
        super().__init__("network")
        self.clk = Input(1, "clk")
        self.reset = Input(1, "reset")

        # Injection ports
        for i in range(MESH_SIZE * MESH_SIZE):
            setattr(self, f"inj_{i}", Input(FLIT_WIDTH, f"inj_{i}"))
            setattr(self, f"push_j_{i}", Input(1, f"push_j_{i}"))
            setattr(self, f"w_j_ack_{i}", Input(1, f"w_j_ack_{i}"))

        # Ejection ports
        ej_ports = []
        wrj_ports = []
        je_ports = []
        pja_ports = []
        for i in range(MESH_SIZE * MESH_SIZE):
            ej_ports.append(Output(FLIT_WIDTH, f"ej_{i}"))
            wrj_ports.append(Output(1, f"write_req_j_{i}"))
            je_ports.append(Output(1, f"j_e_{i}"))
            pja_ports.append(Output(1, f"push_j_ack_{i}"))
            setattr(self, f"ej_{i}", ej_ports[-1])
            setattr(self, f"write_req_j_{i}", wrj_ports[-1])
            setattr(self, f"j_e_{i}", je_ports[-1])
            setattr(self, f"push_j_ack_{i}", pja_ports[-1])

        # Internal mesh links
        east = [Wire(FLIT_WIDTH, f"east_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        west = [Wire(FLIT_WIDTH, f"west_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        north = [Wire(FLIT_WIDTH, f"north_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        south = [Wire(FLIT_WIDTH, f"south_{i}") for i in range(MESH_SIZE * MESH_SIZE)]

        E_en = [Wire(1, f"E_en_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        W_en = [Wire(1, f"W_en_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        N_en = [Wire(1, f"N_en_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        S_en = [Wire(1, f"S_en_{i}") for i in range(MESH_SIZE * MESH_SIZE)]

        E_req = [Wire(1, f"E_req_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        W_req = [Wire(1, f"W_req_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        N_req = [Wire(1, f"N_req_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        S_req = [Wire(1, f"S_req_{i}") for i in range(MESH_SIZE * MESH_SIZE)]

        E_ack = [Wire(1, f"E_ack_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        W_ack = [Wire(1, f"W_ack_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        N_ack = [Wire(1, f"N_ack_{i}") for i in range(MESH_SIZE * MESH_SIZE)]
        S_ack = [Wire(1, f"S_ack_{i}") for i in range(MESH_SIZE * MESH_SIZE)]

        # Lists for output assignment (avoid getattr on LHS of <<=)
        ej_list = ej_ports
        wrj_list = wrj_ports
        je_list = je_ports

        # Instantiate 64 Process_Nodes
        for y in range(MESH_SIZE):
            for x in range(MESH_SIZE):
                idx = y * MESH_SIZE + x
                node = ProcessNode()

                # Determine neighbor indices
                west_idx = y * MESH_SIZE + (x - 1) if x > 0 else -1
                east_idx = y * MESH_SIZE + (x + 1) if x < MESH_SIZE - 1 else -1
                north_idx = (y - 1) * MESH_SIZE + x if y > 0 else -1
                south_idx = (y + 1) * MESH_SIZE + x if y < MESH_SIZE - 1 else -1

                # West input
                iw = west[idx] if x < MESH_SIZE - 1 else Const(0, FLIT_WIDTH)
                push_w = W_req[idx] if x < MESH_SIZE - 1 else Const(0, 1)
                w_state = W_en[idx] if x < MESH_SIZE - 1 else Const(0, 1)
                w_w_ack = W_ack[idx] if x < MESH_SIZE - 1 else Const(0, 1)
                push_w_ack = W_ack[idx] if x < MESH_SIZE - 1 else Wire(1, f"pwa_{idx}")

                # East input
                ie = east[idx] if x > 0 else Const(0, FLIT_WIDTH)
                push_e = E_req[idx] if x > 0 else Const(0, 1)
                e_state = E_en[idx] if x > 0 else Const(0, 1)
                w_e_ack = E_ack[idx] if x > 0 else Const(0, 1)
                push_e_ack = E_ack[idx] if x > 0 else Wire(1, f"pea_{idx}")

                # North input
                in_ = north[idx] if y < MESH_SIZE - 1 else Const(0, FLIT_WIDTH)
                push_n = N_req[idx] if y < MESH_SIZE - 1 else Const(0, 1)
                n_state = N_en[idx] if y < MESH_SIZE - 1 else Const(0, 1)
                w_n_ack = N_ack[idx] if y < MESH_SIZE - 1 else Const(0, 1)
                push_n_ack = N_ack[idx] if y < MESH_SIZE - 1 else Wire(1, f"pna_{idx}")

                # South input
                is_ = south[idx] if y > 0 else Const(0, FLIT_WIDTH)
                push_s = S_req[idx] if y > 0 else Const(0, 1)
                s_state = S_en[idx] if y > 0 else Const(0, 1)
                w_s_ack = S_ack[idx] if y > 0 else Const(0, 1)
                push_s_ack = S_ack[idx] if y > 0 else Wire(1, f"psa_{idx}")

                # Outputs
                w_oe = Wire(FLIT_WIDTH, f"oe_{idx}")
                w_ow = Wire(FLIT_WIDTH, f"ow_{idx}")
                w_on = Wire(FLIT_WIDTH, f"on_{idx}")
                w_os = Wire(FLIT_WIDTH, f"os_{idx}")
                w_ej = Wire(FLIT_WIDTH, f"w_ej_{idx}")

                w_wre = Wire(1, f"wre_{idx}")
                w_wrw = Wire(1, f"wrw_{idx}")
                w_wrn = Wire(1, f"wrn_{idx}")
                w_wrs = Wire(1, f"wrs_{idx}")
                w_wrj = Wire(1, f"wrj_{idx}")

                w_ee = Wire(1, f"ee_{idx}")
                w_we = Wire(1, f"we_{idx}")
                w_ne = Wire(1, f"ne_{idx}")
                w_se = Wire(1, f"se_{idx}")
                w_je = Wire(1, f"je_{idx}")

                self.instantiate(node, f"p{idx}", port_map={
                    "X_cur": Const(x, X_WIDTH), "Y_cur": Const(y, Y_WIDTH),
                    "ie": ie, "iw": iw, "in_": in_, "is_": is_,
                    "clk": self.clk, "reset": self.reset,
                    "push_e": push_e, "push_w": push_w,
                    "push_n": push_n, "push_s": push_s,
                    "e_state": e_state, "w_state": w_state,
                    "n_state": n_state, "s_state": s_state,
                    "oe": w_oe, "ow": w_ow, "on_": w_on, "os_": w_os,
                    "write_req_e": w_wre, "write_req_w": w_wrw,
                    "write_req_n": w_wrn, "write_req_s": w_wrs,
                    "e_e": w_ee, "w_e": w_we, "n_e": w_ne, "s_e": w_se,
                    "w_e_ack": w_e_ack, "w_w_ack": w_w_ack,
                    "w_n_ack": w_n_ack, "w_s_ack": w_s_ack,
                    "push_e_ack": push_e_ack, "push_w_ack": push_w_ack,
                    "push_n_ack": push_n_ack, "push_s_ack": push_s_ack,
                    "inject": getattr(self, f"inj_{idx}"),
                    "push_j": getattr(self, f"push_j_{idx}"),
                    "w_j_ack": getattr(self, f"w_j_ack_{idx}"),
                    "write_req_j": w_wrj, "j_e": w_je,
                    "push_j_ack": getattr(self, f"push_j_ack_{idx}"),
                    "eject": w_ej,
                })

                # Connect outputs to neighbor links
                if x < MESH_SIZE - 1:
                    east[idx] <<= w_oe
                    E_en[idx] <<= w_ee
                    E_req[idx] <<= w_wre
                    E_ack[idx] <<= w_wre
                if x > 0:
                    west[idx] <<= w_ow
                    W_en[idx] <<= w_we
                    W_req[idx] <<= w_wrw
                    W_ack[idx] <<= w_wrw
                if y < MESH_SIZE - 1:
                    north[idx] <<= w_on
                    N_en[idx] <<= w_ne
                    N_req[idx] <<= w_wrn
                    N_ack[idx] <<= w_wrn
                if y > 0:
                    south[idx] <<= w_os
                    S_en[idx] <<= w_se
                    S_req[idx] <<= w_wrs
                    S_ack[idx] <<= w_wrs

                # Eject output (stored in list for assignment)
                ej_list[idx] <<= w_ej
                wrj_list[idx] <<= w_wrj
                je_list[idx] <<= w_je
