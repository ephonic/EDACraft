* Differential Pair — source-coupled pair + active load
* AC analysis for differential gain

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.5
VIN_P vip 0 0.75 AC 0.5
VIN_N vin 0 0.75 AC 0.5
Iss 0 vss_tail 200u

* Diff pair
M1 d1 vip vss_tail 0 nmos w=5u l=130n
M2 d2 vin vss_tail 0 nmos w=5u l=130n

* Active load (current mirror load)
M3 d1 d1 vdd vdd pmos w=10u l=130n
M4 d2 d1 vdd vdd pmos w=10u l=130n

* Output load
Cout d2 0 1p

.op
.ac dec 50 1k 100meg
.print v(d2)
.end
