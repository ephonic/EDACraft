* inv with known-good bsim4 params
vdd vdd 0 1.8
vin in 0 pulse(0 1.8 1n 0.1n 0.1n 8n 15n)
m1 out in vdd vdd pmos w=2e-6 l=2e-7
m2 out in 0   0 nmos w=1e-6 l=2e-7
.model nmos bsim4va file="models/bsim4.dll"
+ toxe=3e-9 toxp=3e-9 vth0=0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032 u0=0.045 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
.model pmos bsim4va file="models/bsim4.dll"
+ toxe=3e-9 toxp=3e-9 vth0=-0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032 u0=0.015 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
.op
.tran 0.1n 15n
.print v(in) v(out)
.end
