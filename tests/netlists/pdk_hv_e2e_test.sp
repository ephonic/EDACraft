* HV PDK end-to-end (smaller, avoids 138K-line LC file): TT corner, level=54
VDD vdd 0 1.8
RD  vdd d  10k
VG  g   0  1.0
M1 d g 0 0 nch_hv18 w=2u l=180n
.lib 'pdk/models/hspice/cln28hpcp_hv_1d8_elk_v0d1_2p1_shrink0d9_embedded_usage.l' TTMacro_MOS_MOSCAP
.op
.print v(d) i(vdd)
.end
