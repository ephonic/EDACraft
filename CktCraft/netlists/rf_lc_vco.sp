* LC VCO for PLL — 2.4GHz, varactor tuning
* AC analysis for tuning range

.include bsim4_nmos.inc

VDD vdd 0 1.2
Vtune tune 0 0.6

* LC tank with varactor (MOS cap)
L1 vdd out1 3n
L2 vdd out2 3n
C1 out1 out2 500f

* Varactor (MOS as voltage-dependent capacitor)
Mvar1 out1 tune 0 0 nmos w=20u l=130n
Mvar2 out2 tune 0 0 nmos w=20u l=130n

* Cross-coupled pair
M1 out1 out2 vss 0 nmos w=5u l=130n
M2 out2 out1 vss 0 nmos w=5u l=130n
Iss 0 vss 2m

.op
.ac dec 50 1meg 10g
.print v(out1)
.end
