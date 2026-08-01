* nmos_sh 共源 — openvaf
VDD vdd 0 2.0
RD  vdd d  1k
VG  g   0 1.5
M1  d g 0 0 nmos_sh
.model nmos_sh nmos_sh file="G:/vibe-codeing/simulator/CktCraft/models/nmos_sh.dll" vth0=0.7 kp=50e-6 lambda=0.02
.op
.print v(d) i(vdd)
.end
