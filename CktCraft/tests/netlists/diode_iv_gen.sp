* Diode I-V sweep — generated model (rfsim_codegen, generated=1)
* Baseline: diode_iv_osdi.sp (openvaf dll, same circuit)

VDD vdd 0 5
R1 vdd a 1k
D1 a 0 simple_diode

.model simple_diode simple_diode generated=1

.dc VDD 0 5 0.05
.print v(a)
.end
