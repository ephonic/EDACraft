* 32-Finger Current Mirror Array — 1 reference + 31 mirrors
* 镜像管 gate 共享, 大部分器件在静态偏置
* multi-rate 理想测试场景

.include bsim4_nmos.inc

VDD vdd 0 1.5
VREF ref 0 0.7 SIN(0.7 0.01 1meg)

Mref ref ref vss 0 nmos w=1u l=130n
Rref vdd ref 10k

* 31 个镜像管, gate=ref, drain 各接 R 到 VDD
.subckt mirror gate drain vdd
+ params: rd=10k
Rd vdd drain rd
Mn drain gate 0 0 nmos w=1u l=130n
.ends

X1 ref m1 vdd mirror
X2 ref m2 vdd mirror
X3 ref m3 vdd mirror
X4 ref m4 vdd mirror
X5 ref m5 vdd mirror
X6 ref m6 vdd mirror
X7 ref m7 vdd mirror
X8 ref m8 vdd mirror
X9 ref m9 vdd mirror
X10 ref m10 vdd mirror
X11 ref m11 vdd mirror
X12 ref m12 vdd mirror
X13 ref m13 vdd mirror
X14 ref m14 vdd mirror
X15 ref m15 vdd mirror
X16 ref m16 vdd mirror
X17 ref m17 vdd mirror
X18 ref m18 vdd mirror
X19 ref m19 vdd mirror
X20 ref m20 vdd mirror
X21 ref m21 vdd mirror
X22 ref m22 vdd mirror
X23 ref m23 vdd mirror
X24 ref m24 vdd mirror
X25 ref m25 vdd mirror
X26 ref m26 vdd mirror
X27 ref m27 vdd mirror
X28 ref m28 vdd mirror
X29 ref m29 vdd mirror
X30 ref m30 vdd mirror
X31 ref m31 vdd mirror

.op
.ac dec 50 1k 1g
.print v(m1) v(m16) v(m31)
.end
