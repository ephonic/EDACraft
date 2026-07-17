* NAND Gate — 2-input CMOS NAND
* DC sweep for transfer characteristics

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.2
VA  a   0 0.6
VB  b   0 1.2

* NMOS series (pull-down network)
M1n out a x 0 nmos w=1u l=130n
M2n x b 0 0 nmos w=1u l=130n

* PMOS parallel (pull-up network)
M1p out a vdd vdd pmos w=2u l=130n
M2p out b vdd vdd pmos w=2u l=130n

Cload out 0 10f

.dc VA 0 1.2 0.1
.print v(out)
.end
