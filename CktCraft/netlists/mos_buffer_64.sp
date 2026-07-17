* 64-Finger Buffer Chain — 8x8 矩阵 inverter buffer
* 64 个 BSIM4 (32 NMOS + 32 PMOS), 大规模 CMOS
* 测试大规模 DC OP + AC

.include bsim4_nmos.inc
.include bsim4_pmos.inc

VDD vdd 0 1.2
VIN in 0 0.6 AC 1

* 8x8 inverter 矩阵 (64 个 inverter = 128 个 MOS)
.subckt inv in out vdd gnd
Mn out in gnd gnd nmos w=1u l=130n
Mp out in vdd vdd pmos w=2u l=130n
.ends

X1 in s1a vdd 0 inv
X2 in s1b vdd 0 inv
X3 in s1c vdd 0 inv
X4 in s1d vdd 0 inv
X5 in s1e vdd 0 inv
X6 in s1f vdd 0 inv
X7 in s1g vdd 0 inv
X8 in s1h vdd 0 inv

X9 s1a s2a vdd 0 inv
X10 s1b s2b vdd 0 inv
X11 s1c s2c vdd 0 inv
X12 s1d s2d vdd 0 inv
X13 s1e s2e vdd 0 inv
X14 s1f s2f vdd 0 inv
X15 s1g s2g vdd 0 inv
X16 s1h s2h vdd 0 inv

X17 s2a s3a vdd 0 inv
X18 s2b s3b vdd 0 inv
X19 s2c s3c vdd 0 inv
X20 s2d s3d vdd 0 inv
X21 s2e s3e vdd 0 inv
X22 s2f s3f vdd 0 inv
X23 s2g s3g vdd 0 inv
X24 s2h s3h vdd 0 inv

X25 s3a out1 vdd 0 inv
X26 s3b out2 vdd 0 inv
X27 s3c out3 vdd 0 inv
X28 s3d out4 vdd 0 inv
X29 s3e out5 vdd 0 inv
X30 s3f out6 vdd 0 inv
X31 s3g out7 vdd 0 inv
X32 s3h out8 vdd 0 inv

Cload out1 0 10f
Cload out2 0 10f
Cload out3 0 10f
Cload out4 0 10f
Cload out5 0 10f
Cload out6 0 10f
Cload out7 0 10f
Cload out8 0 10f

.op
.ac dec 20 1k 1g
.print v(out1) v(out8)
.end
