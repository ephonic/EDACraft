* BSIM4 rfsim test — WITH all critical BSIM4.8 default parameters
* Matches HSPICE level=54 built-in defaults for key subthreshold params
VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.7

M1 d g 0 0 nmos w=1u l=130n

.model nmos bsim4va generated=1
+ toxe=3e-9 toxp=3e-9
+ vth0=0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032
+ u0=0.045 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
+ cjs=1e-3 cjd=1e-3 cjsws=1e-10 cjswd=1e-10
+ mjs=0.5 mjd=0.5 mjsws=0.33 mjswd=0.33
+ pbs=0.88 pbd=0.88 pbsws=0.88 pbswd=0.88
* Critical subthreshold params (BSIM4.8 defaults from HSPICE):
+ voff=-0.128 noff=0.5
+ cdsc=0.0 cdscb=0.0 cdscd=0.0
+ eta0=0.08 dsub=0.56
+ pdiblc1=0.0 pdiblc2=0.0 pdiblcb=0.0
+ drout=0.0

.dc VG 0.0 1.2 0.05
.print v(d) i(VDD)
.end
