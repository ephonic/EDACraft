* BSIM4 VA apple-to-apple: HSPICE pva vs rfsim codegen, same bsim4.va
* HSPICE loads VA module via .hdl, instantiates as subcircuit X
.hdl "bsim4.va"

VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.7

X1 d g 0 0 bsim4va
+ w=1u l=130n
+ toxe=3e-9 toxp=3e-9
+ vth0=0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032
+ u0=0.045 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
+ cjs=1e-3 cjd=1e-3 cjsws=1e-10 cjswd=1e-10
+ mjs=0.5 mjd=0.5 mjsws=0.33 mjswd=0.33
+ pbs=0.88 pbd=0.88 pbsws=0.88 pbswd=0.88

.op
.print dc v(d) v(g) i(VDD)
.temp 27
.end
