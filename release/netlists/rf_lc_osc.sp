* RF LC Oscillator — 1GHz cross-coupled NMOS pair
* Cross-coupled pair + LC tank, PSS at 1GHz

.include bsim4_nmos.inc

VDD vdd 0 1.5
 Iss 0 vss 1m

* LC tank
L1 vdd out1 5n
L2 vdd out2 5n
C1 out1 out2 1p
R1 out1 0 1k
R2 out2 0 1k

* Cross-coupled pair
M1 out1 out2 vss 0 nmos w=2u l=130n
M2 out2 out1 vss 0 nmos w=2u l=130n

.pss freq=1g nh=3 pts=64
.print v(out1) v(out2)
.end
