IVERILOG = iverilog
VVP = vvp
FLAGS = -g2012 -Wall

.PHONY: all simd16 sram apb_bridge qspi i2c top clean
all: simd16 sram apb_bridge qspi i2c top

simd16:
	$(IVERILOG) $(FLAGS) -o sim_simd16.vvp ../../verilog/earphone_simd16.v tb_earphone_simd16.v
	$(VVP) sim_simd16.vvp

sram:
	$(IVERILOG) $(FLAGS) -o sim_sram.vvp ../../verilog/earphone_sram256k.v tb_earphone_sram256k.v
	$(VVP) sim_sram.vvp

apb_bridge:
	$(IVERILOG) $(FLAGS) -o sim_apb_bridge.vvp ../../verilog/earphone_apb_bridge.v tb_earphone_apb_bridge.v
	$(VVP) sim_apb_bridge.vvp

qspi:
	$(IVERILOG) $(FLAGS) -o sim_qspi.vvp ../../verilog/earphone_qspi.v tb_earphone_qspi.v
	$(VVP) sim_qspi.vvp

i2c:
	$(IVERILOG) $(FLAGS) -o sim_i2c.vvp ../../verilog/earphone_i2c.v tb_earphone_i2c.v
	$(VVP) sim_i2c.vvp

clean:
	rm -f *.vvp

top:
	$(IVERILOG) $(FLAGS) -o sim_top.vvp \
	    ../../verilog/earphone_top.v \
	    ../../verilog/earphone_rv32.v \
	    ../../verilog/earphone_simd16.v \
	    ../../verilog/earphone_fft256.v \
	    ../../verilog/fft_controller_256.v \
	    ../../verilog/earphone_qspi.v \
	    ../../verilog/earphone_i2c.v \
	    ../../verilog/earphone_sram256k.v \
	    ../../verilog/earphone_apb_bridge.v \
	    tb_earphone_top.v
	$(VVP) sim_top.vvp
