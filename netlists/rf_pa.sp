* RF Power Amplifier — class AB single-stage
* 900MHz, 1.2V supply, output matched to 50ohm

.include bsim4_nmos.inc

VDD vdd 0 1.2
VB  b  0 0.8
VIN in 0 0.8 SIN(0.8 0.3 900meg)

L1 vdd d 10n
C1 d out 1p
RL out 0 50
Rb b in 1k

M1 d b 0 0 nmos w=100u l=130n

.pss freq=900meg nh=5 pts=64
.print v(out) v(d)
.end
