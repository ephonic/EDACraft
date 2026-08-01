* ekv 共源 — generated (默认参数)
VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.55
M1  d g 0 0 ekv_va
.model ekv_va ekv_va generated=1
.op
.print v(d) i(vdd)
.end
