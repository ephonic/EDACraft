* full diode.va generated model (rs=0.1, cj0, temp effects), DC op
VDD vdd 0 5
R1 vdd a 1k
D1 a 0 0 diode_va
.model diode_va diode_va generated=1 rs=0.1 cj0=1e-12
.op
.print v(a) i(vdd)
.end
