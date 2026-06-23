* 4-Bit Flash ADC — 15 comparators + resistor ladder
* 16 个 BSIM4 (8 比较器对) + 15 级电阻 ladder
* 测试大规模混合 DC + AC

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.2
VIN in 0 0.6 AC 1

* 电阻 ladder (15 个电阻 = 16 级)
R1 vdd r1 100
R2 r1 r2 100
R3 r2 r3 100
R4 r3 r4 100
R5 r4 r5 100
R6 r5 r6 100
R7 r6 r7 100
R8 r7 r8 100
R9 r8 r9 100
R10 r9 r10 100
R11 r10 r11 100
R12 r11 r12 100
R13 r12 r13 100
R14 r13 r14 100
R15 r14 0 100

* 8 个比较器 (每个 2 MOS: NMOS + PMOS)
.subckt cmp in ref out vdd
Mn out in 0 0 nmos w=2u l=130n
Mp out ref vdd vdd pmos w=4u l=130n
.ends

Xc1 in r1 o1 vdd cmp
Xc2 in r3 o2 vdd cmp
Xc3 in r5 o3 vdd cmp
Xc4 in r7 o4 vdd cmp
Xc5 in r9 o5 vdd cmp
Xc6 in r11 o6 vdd cmp
Xc7 in r13 o7 vdd cmp
Xc8 in r15 o8 vdd cmp

Cload o1 0 10f
Cload o2 0 10f
Cload o3 0 10f
Cload o4 0 10f
Cload o5 0 10f
Cload o6 0 10f
Cload o7 0 10f
Cload o8 0 10f

.op
.ac dec 20 1k 1g
.print v(o1) v(o4) v(o8)
.end
