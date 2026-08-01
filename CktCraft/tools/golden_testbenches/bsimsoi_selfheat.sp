* BSIMSOI with self-heating (shmod=1, rth0=0.05)
VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.7
M1 d g 0 0 nmos w=1u l=130n
.model nmos bsimsoi
+ type=1 tox=3e-9 toxp=3e-9 toxm=3e-9
+ vtho=0.5 vth0=0.5 u0=0.045 vsat=1.5e5
+ rdsw=160 cgso=0.1e-9 cgdo=0.1e-9 voff=-0.08
+ shmod=1 rth0=0.05 cth0=1e-5
.op
.print v(d) i(VDD)
.end
