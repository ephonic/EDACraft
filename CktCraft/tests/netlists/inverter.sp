* rfsim M1 示例网表: CMOS 反相器 + 子电路 + .param 表达式
* 标题行（SPICE 第一行）

.param vdd = 1.2
.param wn = 1u
.param wp = '2*wn'
.param rl = 1k

VDD vdd 0 {vdd}
VIN in 0 PULSE(0 1.2 0 1n 1n 5n 10n)

* 反相器子电路
.subckt inv in out vdd gnd
+ params: wn=1u wp=2u
Mn1 out in gnd gnd nmos w=wn l=180n
Mp1 out in vdd vdd pmos w=wp l=180n
.ends

Xinv1 in out vdd 0 inv wn=1u wp=2u

Rload out 0 rl
Cload out 0 1p

.model nmos nmos level=1 vt0=0.5 kp=50u
.model pmos pmos level=1 vt0=-0.5 kp=20u

.hb freq=2.5G nh=5
.print v(out) v(in)
.measure gain find v(out) at=1n

.options reltol=1e-6 abstol=1e-12

.end
