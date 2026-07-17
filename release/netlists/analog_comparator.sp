* Comparator — cascaded inverter chain (3 stages)
* High gain open-loop comparator

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.5
VIN in 0 0.75 AC 1

* Stage 1: low gain, wide bandwidth
M1n s1 in 0 0 nmos w=2u l=130n
M1p s1 in vdd vdd pmos w=4u l=130n

* Stage 2: medium gain
M2n s2 s1 0 0 nmos w=4u l=130n
M2p s2 s1 vdd vdd pmos w=8u l=130n

* Stage 3: high gain, large
M3n out s2 0 0 nmos w=10u l=130n
M3p out s2 vdd vdd pmos w=20u l=130n

.op
.ac dec 50 1 1g
.print v(out)
.end
