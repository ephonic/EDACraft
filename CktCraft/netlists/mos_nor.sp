* NOR Gate — 2-input CMOS NOR
* AC transfer characteristics

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.2
VA  a   0 0.6 AC 1
VB  b   0 0

* NMOS parallel (pull-down)
M1n out a 0 0 nmos w=1u l=130n
M2n out b 0 0 nmos w=1u l=130n

* PMOS series (pull-up)
M1p out a x vdd pmos w=2u l=130n
M2p x b vdd vdd pmos w=2u l=130n

Cload out 0 10f

.dc VA 0 1.2 0.1
.ac dec 50 1 1g
.print v(out)
.end
