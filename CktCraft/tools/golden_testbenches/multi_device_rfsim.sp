* Multi-Device Circuit Test - combines BSIM4, BSIM3, BJT, Diode
* Topology: BJT input -> BSIM3 gain -> BSIM4 output -> Diode clamp

* Power supplies
VCC vcc 0 3.0
VDD vdd 0 1.0

* Input signal
VIN in 0 0.7

* Stage 1: BJT common-emitter amplifier
RC1 vcc c1 10k
Q1 c1 in 0 0 bjt_npn

* Stage 2: BSIM3 common-source amplifier (level-shifted)
RB1 c1 g2 100k
RD2 vdd d2 1k
M2 d2 g2 0 0 nmos_b3 w=1u l=130n

* Stage 3: BSIM4 output buffer
RD3 vdd d3 500
M3 d3 d2 0 0 nmos_b4 w=2u l=130n

* Diode clamp on output
D1 d3 0 clamp_diode

* Models
.model bjt_npn bjt505va generated=1
+ type=1 is=1e-16 bf=100 vaf=50 re=1 rc=10 rb=100 tref=25

.model nmos_b3 bsim3_va generated=1
+ toxe=3e-9 toxp=3e-9 vth0=0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032 u0=0.045 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
+ cjs=1e-3 cjd=1e-3 cjsws=1e-10 cjswd=1e-10
+ mjs=0.5 mjd=0.5 mjsws=0.33 mjswd=0.33
+ pbs=0.88 pbd=0.88 pbsws=0.88 pbswd=0.88
+ voff=-0.08

.model nmos_b4 bsim4va generated=1
+ toxe=3e-9 toxp=3e-9 vth0=0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032 u0=0.045 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
+ cjs=1e-3 cjd=1e-3 cjsws=1e-10 cjswd=1e-10
+ mjs=0.5 mjd=0.5 mjsws=0.33 mjswd=0.33
+ pbs=0.88 pbd=0.88 pbsws=0.88 pbswd=0.88

.model clamp_diode diode_va generated=1
+ is=1e-14 n=1.0 rs=10 cj0=1p vj=0.7 m=0.5

.op
.print v(in) v(c1) v(g2) v(d2) v(d3) i(VCC) i(VDD)
.end
