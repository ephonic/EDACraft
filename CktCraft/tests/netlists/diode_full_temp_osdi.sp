* full diode.va openvaf baseline at 75C (temp-dependent Is)
VDD vdd 0 1.5
R1 vdd a 1k
D1 a 0 0 diode_va
.model diode_va diode_va file="G:/vibe-codeing/simulator/CktCraft/models/diode.dll" rs=0.1
.options temp=75
.op
.print v(a) i(vdd)
.end
