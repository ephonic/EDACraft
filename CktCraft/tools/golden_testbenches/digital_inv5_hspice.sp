* 5-stage CMOS Inverter Chain — HSPICE golden
* PTM 130nm BSIM4 model, VDD=1.0V

VDD vdd 0 1.0
VIN in 0 PULSE(0 1 0.5n 100p 100p 1n 2n)

* Stage 1
MP1 mid1 in vdd vdd pmos w=2u l=130n
MN1 mid1 in 0 0 nmos w=1u l=130n

* Stage 2
MP2 mid2 mid1 vdd vdd pmos w=2u l=130n
MN2 mid2 mid1 0 0 nmos w=1u l=130n

* Stage 3
MP3 mid3 mid2 vdd vdd pmos w=2u l=130n
MN3 mid3 mid2 0 0 nmos w=1u l=130n

* Stage 4
MP4 mid4 mid3 vdd vdd pmos w=2u l=130n
MN4 mid4 mid3 0 0 nmos w=1u l=130n

* Stage 5
MP5 out mid4 vdd vdd pmos w=2u l=130n
MN5 out mid4 0 0 nmos w=1u l=130n

CL out 0 50f

.model nmos nmos level=54
+ toxe=3.0e-9 toxp=3.0e-9 toxm=3.0e-9
+ nsub=1.7e17 ndep=1.7e17 nsd=2.0e20
+ vth0=0.4271 k1=0.3031 k2=-0.0191 k3=80 k3b=0
+ vbm=-4.0 vbx=0.6391 gamma1=0.3875 gamma2=0.0
+ dvt0=2.2 dvt1=0.53 dvt2=-0.032
+ drout=0.56 dsub=0.56 eta0=0.08 etab=-0.07
+ pdiblc1=0.39 pdiblc2=0.0086 pdiblcb=0
+ u0=0.0421 ua=-1.41e-9 ub=2.08e-18 uc=-4.65e-11
+ eu=1.67 vsat=8.24e4 nfactor=1.5
+ rdsw=165 voff=-0.128
+ pclm=1.3 pscbe1=4.25e6 pscbe2=1e-5
+ cgso=2e-10 cgdo=2e-10 cgbo=0
+ cjs=1e-3 cjd=1e-3 pbs=0.88 pbd=0.88
+ mjs=0.5 mjd=0.5 mjsws=0.33 mjswd=0.33
+ delta=0.01 xj=0.15e-6
+ kt1=-0.35 kt2=-0.042 ute=-1.48

.model pmos pmos level=54
+ toxe=3.0e-9 toxp=3.0e-9 toxm=3.0e-9
+ nsub=2.0e17 ndep=2.0e17 nsd=2.0e20
+ vth0=-0.4014 k1=0.35 k2=-0.02 k3=80 k3b=0
+ vbm=-4.0 vbx=0.65 gamma1=0.40 gamma2=0.0
+ dvt0=2.0 dvt1=0.50 dvt2=-0.03
+ drout=0.56 dsub=0.56 eta0=0.08 etab=-0.07
+ pdiblc1=0.39 pdiblc2=0.0086 pdiblcb=0
+ u0=0.025 ua=-1.0e-9 ub=2.0e-18 uc=-4.65e-11
+ eu=1.67 vsat=8.0e4 nfactor=1.6
+ rdsw=180 voff=-0.13
+ pclm=1.3 pscbe1=4.25e6 pscbe2=1e-5
+ cgso=2e-10 cgdo=2e-10 cgbo=0
+ cjs=1e-3 cjd=1e-3 pbs=0.88 pbd=0.88
+ mjs=0.5 mjd=0.5 mjsws=0.33 mjswd=0.33
+ delta=0.01 xj=0.15e-6
+ kt1=-0.35 kt2=-0.042 ute=-1.48

.dc VIN 0 1 0.05
.print dc v(in) v(mid1) v(mid2) v(mid3) v(mid4) v(out) i(VDD)
.temp 27
.end
