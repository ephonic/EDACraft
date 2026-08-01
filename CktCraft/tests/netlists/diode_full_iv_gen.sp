* full diode.va generated model, I-V sweep (rs=0.1 cj0=1e-12)
VDD vdd 0 5
R1 vdd a 1k
D1 a 0 0 diode_va
.model diode_va diode_va generated=1 rs=0.1 cj0=1e-12
.dc VDD 0 5 0.05
.print v(a)
.end
