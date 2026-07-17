* Inverter Chain — 5 cascaded CMOS inverters
* PSS at 100MHz for propagation delay measurement

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.2
VIN in 0 0.6 SIN(0.6 0.6 100meg)

* 5-stage inverter chain
M1n s1 in 0 0 nmos w=1u l=130n
M1p s1 in vdd vdd pmos w=2u l=130n

M2n s2 s1 0 0 nmos w=1u l=130n
M2p s2 s1 vdd vdd pmos w=2u l=130n

M3n s3 s2 0 0 nmos w=1u l=130n
M3p s3 s2 vdd vdd pmos w=2u l=130n

M4n s4 s3 0 0 nmos w=1u l=130n
M4p s4 s3 vdd vdd pmos w=2u l=130n

M5n out s4 0 0 nmos w=1u l=130n
M5p out s4 vdd vdd pmos w=2u l=130n

* Load capacitance
Cload out 0 100f

.pss freq=100meg nh=5 pts=64
.print v(out) v(s1) v(s3)
.end
