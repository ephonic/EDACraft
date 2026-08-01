* Bypass performance test: 5-stage BSIM4 inverter chain
VDD vdd 0 1.0
VIN in 0 PULSE(0 1 1n 100p 100p 5n 10n)
MP1 mid1 in vdd vdd nmos w=2u l=130n
MN1 mid1 in 0 0 nmos w=1u l=130n
MP2 mid2 mid1 vdd vdd nmos w=2u l=130n
MN2 mid2 mid1 0 0 nmos w=1u l=130n
MP3 mid3 mid2 vdd vdd nmos w=2u l=130n
MN3 mid3 mid2 0 0 nmos w=1u l=130n
MP4 mid4 mid3 vdd vdd nmos w=2u l=130n
MN4 mid4 mid3 0 0 nmos w=1u l=130n
MP5 out mid4 vdd vdd nmos w=2u l=130n
MN5 out mid4 0 0 nmos w=1u l=130n
CL out 0 50f
.model nmos bsim4va
+ toxe=3e-9 toxp=3e-9 vth0=0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032 u0=0.045 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
+ cjs=1e-3 cjd=1e-3 cjsws=1e-10 cjswd=1e-10
+ mjs=0.5 mjd=0.5 mjsws=0.33 mjswd=0.33
+ pbs=0.88 pbd=0.88 pbsws=0.88 pbswd=0.88
.op
.print v(in) v(mid1) v(mid2) v(mid3) v(mid4) v(out)
.end
