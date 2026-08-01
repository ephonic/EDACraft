* Test OSDI fallback with file= (generated=0 implicit)
VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.7
M1 d g 0 0 nmos w=1u l=130n
.model nmos bsim4va file="models/bsim4.dll"
+ toxe=3e-9 toxp=3e-9 vth0=0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032 u0=0.045 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
.op
.print v(d) i(VDD)
.end
