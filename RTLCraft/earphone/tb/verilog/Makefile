# iverilog-based Verilog testbench runner for generated Earphone modules.
# This replaces the cocotb-based plan item because cocotb cannot be installed
# in this environment (PyPI/conda network access is unavailable).

IVERILOG = iverilog
VVP = vvp
VFLAGS = -g2012
RTL_DIR = ../../verilog

TESTS = simd16 sram256k apb_bridge qspi i2c fft256

.PHONY: all clean $(TESTS)

all: $(TESTS)

simd16:
	$(IVERILOG) $(VFLAGS) -o sim_simd16.vvp $(RTL_DIR)/earphone_simd16.v tb_earphone_simd16.v
	$(VVP) sim_simd16.vvp

sram256k:
	$(IVERILOG) $(VFLAGS) -o sim_sram256k.vvp $(RTL_DIR)/earphone_sram256k.v tb_earphone_sram256k.v
	$(VVP) sim_sram256k.vvp

apb_bridge:
	$(IVERILOG) $(VFLAGS) -o sim_apb_bridge.vvp $(RTL_DIR)/earphone_apb_bridge.v tb_earphone_apb_bridge.v
	$(VVP) sim_apb_bridge.vvp

qspi:
	$(IVERILOG) $(VFLAGS) -o sim_qspi.vvp $(RTL_DIR)/earphone_qspi.v tb_earphone_qspi.v
	$(VVP) sim_qspi.vvp

i2c:
	$(IVERILOG) $(VFLAGS) -o sim_i2c.vvp $(RTL_DIR)/earphone_i2c.v tb_earphone_i2c.v
	$(VVP) sim_i2c.vvp

fft256:
	$(IVERILOG) $(VFLAGS) -o sim_fft256.vvp $(RTL_DIR)/earphone_fft256.v $(RTL_DIR)/fft_controller_256.v tb_earphone_fft256.v
	$(VVP) sim_fft256.vvp

clean:
	rm -f *.vvp
