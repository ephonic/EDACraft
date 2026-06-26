* Direct model test
VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.7
M1 d g 0 0 nmos w=1u l=130n

.model nmos bsim4va file="models/bsim4.dll"
+ toxe=3e-9 vth0=0.5 u0=0.045

.op
.end
