* 8-Stage Ring Oscillator with 8x Fanout — 72 BSIM4
* 8 级环振, 每级 8x 扇出 (1+8=9 MOS/级, 8 级 = 72 MOS)
* 测试大规模 PSS Shooting

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.2

.subckt inv in out vdd gnd
Mn out in gnd gnd nmos w=1u l=130n
Mp out in vdd vdd pmos w=2u l=130n
.ends

* 8 级环振, 每级输出驱动 8 个负载 inv (模拟 fanout=8)
X1 s1 s2 vdd 0 inv
X2 s2 s3 vdd 0 inv
X3 s3 s4 vdd 0 inv
X4 s4 s5 vdd 0 inv
X5 s5 s6 vdd 0 inv
X6 s6 s7 vdd 0 inv
X7 s7 s8 vdd 0 inv
X8 s8 s1 vdd 0 inv

* 每级 8 个负载 (fanout)
Xf1 s2 f1a vdd 0 inv
Xf2 s2 f1b vdd 0 inv
Xf3 s2 f1c vdd 0 inv
Xf4 s2 f1d vdd 0 inv
Xf5 s2 f1e vdd 0 inv
Xf6 s2 f1f vdd 0 inv
Xf7 s2 f1g vdd 0 inv
Xf8 s2 f1h vdd 0 inv

Xf9 s4 f2a vdd 0 inv
Xf10 s4 f2b vdd 0 inv
Xf11 s4 f2c vdd 0 inv
Xf12 s4 f2d vdd 0 inv
Xf13 s4 f2e vdd 0 inv
Xf14 s4 f2f vdd 0 inv
Xf15 s4 f2g vdd 0 inv
Xf16 s4 f2h vdd 0 inv

Xf17 s6 f3a vdd 0 inv
Xf18 s6 f3b vdd 0 inv
Xf19 s6 f3c vdd 0 inv
Xf20 s6 f3d vdd 0 inv
Xf21 s6 f3e vdd 0 inv
Xf22 s6 f3f vdd 0 inv
Xf23 s6 f3g vdd 0 inv
Xf24 s6 f3h vdd 0 inv

Xf25 s8 f4a vdd 0 inv
Xf26 s8 f4b vdd 0 inv
Xf27 s8 f4c vdd 0 inv
Xf28 s8 f4d vdd 0 inv
Xf29 s8 f4e vdd 0 inv
Xf30 s8 f4f vdd 0 inv
Xf31 s8 f4g vdd 0 inv
Xf32 s8 f4h vdd 0 inv

.pss freq=200meg nh=3 pts=32
.print v(s1)
.end
