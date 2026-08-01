* full diode.va openvaf baseline (rs=0.1, cj0), DC op
VDD vdd 0 5
R1 vdd a 1k
D1 a 0 0 diode_va
.model diode_va diode_va file="G:/vibe-codeing/simulator/CktCraft/models/diode.dll" rs=0.1 cj0=1e-12
.op
.print v(a) i(vdd)
.end
