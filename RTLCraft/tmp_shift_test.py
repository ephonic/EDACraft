import sys
sys.path.insert(0, 'g:/code/rtlgen/rtlgen')

from rtlgen import Module, Input, Reg
from rtlgen.logic import If, Else
from rtlgen.sim import Simulator

class TestMod(Module):
    def __init__(self):
        super().__init__("TestMod")
        self.a = Input(16, "a")
        self.b = Reg(8, "b")
        self.c = Reg(8, "c")
        self.d = Reg(8, "d")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.b <<= 0
                self.c <<= 0
                self.d <<= 0
            with Else():
                self.b <<= (self.a + 3) >> 2
                self.c <<= self.a + 3
                self.d <<= (self.a + 3) & 0xFF

m = TestMod()
sim = Simulator(m)
sim.reset("rst_n")

sim.poke("a", 192)
sim.step()
print(f"a=192: b={(192+3)>>2} sim_b={sim.peek('b')} sim_c={sim.peek('c')} sim_d={sim.peek('d')}")

sim.poke("a", 64)
sim.step()
print(f"a=64: b={(64+3)>>2} sim_b={sim.peek('b')} sim_c={sim.peek('c')} sim_d={sim.peek('d')}")
