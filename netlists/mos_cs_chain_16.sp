* 16-Finger Distributed Amplifier — 16 cascaded CS stages
* 每级 1 BSIM4 + RC 负载, 共 16 个 BSIM4
* 信号逐级传播, 后级器件在弱信号区

.include bsim4_nmos.inc

VDD vdd 0 1.2
VIN in 0 0.6 SIN(0.6 0.1 100meg)

* 16 级共源放大器, 每级 Rd=2k + CL=100f
.subckt csamp in out vdd
+ params: w=2u rd=2k cl=100f
Mn out in 0 0 nmos w=w l=130n
Rd vdd out rd
Cl out 0 cl
.ends

X1 in s2 vdd csamp
X2 s2 s3 vdd csamp
X3 s3 s4 vdd csamp
X4 s4 s5 vdd csamp
X5 s5 s6 vdd csamp
X6 s6 s7 vdd csamp
X7 s7 s8 vdd csamp
X8 s8 s9 vdd csamp
X9 s9 s10 vdd csamp
X10 s10 s11 vdd csamp
X11 s11 s12 vdd csamp
X12 s12 s13 vdd csamp
X13 s13 s14 vdd csamp
X14 s14 s15 vdd csamp
X15 s15 s16 vdd csamp
X16 s16 out vdd csamp

.op
.ac dec 50 1k 1g
.print v(out) v(s8)
.end
