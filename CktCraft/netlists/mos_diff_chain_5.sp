* 5-Stage Differential Amplifier Chain — 20 BSIM4
* 5 级差分对, 每级 2 NMOS + 2 PMOS = 4 MOS
* 测试大规模 AC 增益链

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.5
VIN_P vip 0 0.75 AC 0.5
VIN_N vin 0 0.75 AC 0.5
Iss 0 vss 200u

* 5 级差分对链
.subckt diffpair inp inn outp outn vdd vss
M1 d1 inp vss 0 nmos w=5u l=130n
M2 d2 inn vss 0 nmos w=5u l=130n
M3 d1 d1 vdd vdd pmos w=10u l=130n
M4 d2 d1 vdd vdd pmos w=10u l=130n
.ends

X1 vip vin s1p s1n vdd vss diffpair
X2 s1p s1n s2p s2n vdd vss diffpair
X3 s2p s2n s3p s3n vdd vss diffpair
X4 s3p s3n s4p s4n vdd vss diffpair
X5 s4p s4n outp outn vdd vss diffpair

Cload outp 0 100f
Cload outn 0 100f

.op
.ac dec 50 1k 1g
.print v(outp) v(outn)
.end
