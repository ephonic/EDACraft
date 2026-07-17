* Two-stage CMOS Opamp — differential pair + common-source output
* DC gain ~40dB, unity gain freq ~10MHz

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.5
VSS 0 0
VIN_P vip 0 0.75
VIN_N vin 0 0.75 AC 1

* Tail current
Iss 0 vss_tail 100u

* Diff pair (PMOS input)
M1 d1 vip vss_tail 0 nmos w=5u l=130n
M2 d2 vin vss_tail 0 nmos w=5u l=130n
M3 d1 d1 vdd vdd pmos w=10u l=130n
M4 d2 d1 vdd vdd pmos w=10u l=130n

* Second stage (common source)
M5 out d2 vss 0 nmos w=20u l=130n
M6 out d1 vdd vdd pmos w=20u l=130n

* Compensation
Cc out d2 1p
Rc out d2 1k

.op
.ac dec 50 1 100meg
.print v(out)
.end
