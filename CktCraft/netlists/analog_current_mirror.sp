* Current Mirror — N:1 cascoded, 1V reference
* 4 branches: 1 reference + 3 mirrors with different ratios

.include bsim4_nmos.inc

VDD vdd 0 1.5
VREF ref 0 0.7

* Reference branch (diode-connected)
Mref ref ref vss 0 nmos w=1u l=130n
Rref vdd ref 10k

* Mirror 1: 1:1
Rm1 vdd m1 10k
Mm1 m1 ref vss 0 nmos w=1u l=130n

* Mirror 2: 1:2 (2x width)
Rm2 vdd m2 5k
Mm2 m2 ref vss 0 nmos w=2u l=130n

* Mirror 3: 1:4 (4x width)
Rm3 vdd m3 2.5k
Mm3 m3 ref vss 0 nmos w=4u l=130n

.op
.print v(ref) v(m1) v(m2) v(m3)
.end
