* Ring Oscillator — 11-stage, odd number for oscillation
* PSS self-oscillating frequency measurement

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.2

* 11-stage ring oscillator
.subckt inv in out vdd gnd
Mn out in gnd gnd nmos w=1u l=130n
Mp out in vdd vdd pmos w=2u l=130n
.ends

X1 s1 s2 vdd 0 inv
X2 s2 s3 vdd 0 inv
X3 s3 s4 vdd 0 inv
X4 s4 s5 vdd 0 inv
X5 s5 s6 vdd 0 inv
X6 s6 s7 vdd 0 inv
X7 s7 s8 vdd 0 inv
X8 s8 s9 vdd 0 inv
X9 s9 s10 vdd 0 inv
X10 s10 s11 vdd 0 inv
X11 s11 s1 vdd 0 inv

Cload s1 0 50f

.pss freq=500meg nh=3 pts=64
.print v(s1)
.end
