* diode_vt openvaf baseline with elevated temperature (75C = 348.15K)
VDD vdd 0 1.5
R1 vdd a 1k
D1 a 0 diode_vt
.model diode_vt diode_vt file="G:/vibe-codeing/simulator/CktCraft/models/diode_vt.dll"
.options temp=75
.op
.print v(a) i(vdd)
.end
