* Test include
VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.7
M1 d g 0 0 nmos w=1u l=130n

.include "bsim4_nmos.inc"

.op
.end
