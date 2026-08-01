* BSIM4 DC Sweep — FineSim golden reference
* Common-source amplifier: VDD -> RD 1k -> drain; VG -> gate; source/bulk = GND
* Sweep: VG = 0.0 to 1.2V step 0.1V, VDD = {0.5, 1.0, 1.5}V, T = {27, 85, 125}C
* Model: PTM 130nm BSIM4 parameters
*
* Run: finesim -spice bsim4_dc_sweep.sp -o bsim4_dc_sweep.lis

.option post=2 nomod

VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.7

M1 d g 0 0 nmos w=1u l=130n

.model nmos bsim4va
+ toxe=3e-9 toxp=3e-9
+ vth0=0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032
+ u0=0.045 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
+ cjs=1e-3 cjd=1e-3 cjsws=1e-10 cjswd=1e-10
+ mjs=0.5 mjd=0.5 mjsws=0.33 mjswd=0.33
+ pbs=0.88 pbd=0.88 pbsws=0.88 pbswd=0.88

* DC sweep: VG from 0 to 1.2V
.dc VG 0.0 1.2 0.1

.print dc v(d) i(VDD)
.probe dc ids=M1.ids

.temp 27

.end
