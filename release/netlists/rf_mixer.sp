* RF Gilbert Mixer — double-balanced, LO=1GHz, RF=900MHz
* 4 switching MOS + 1 tail + 2 load resistors

.include bsim4_nmos.inc

VDD vdd 0 1.5
VLO lo1 0 0.7 SIN(0.7 0.2 1g)
VLO lo2 0 0.7 SIN(0.7 0.2 1g)
VRF rf1 0 0.7 SIN(0.7 0.01 900meg)
VRF rf2 0 0.7 SIN(0.7 0.01 900meg)

RD1 vdd out1 5k
RD2 vdd out2 5k

M1 out1 lo1 x1 0 nmos w=2u l=130n
M2 out2 lo2 x1 0 nmos w=2u l=130n
M3 out1 lo2 x2 0 nmos w=2u l=130n
M4 out2 lo1 x2 0 nmos w=2u l=130n
M5 x1 rf1 vss 0 nmos w=4u l=130n
M6 x2 rf2 vss 0 nmos w=4u l=130n
Iss 0 vss 1m

.pss freq=1g nh=3 pts=64
.print v(out1) v(out2)
.end
