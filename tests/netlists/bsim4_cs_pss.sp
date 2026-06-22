* rfsim end-to-end: BSIM4 NMOS common-source amplifier @ 1MHz
* VDD=1V, Rd=1k load, Vg = DC 0.7V + AC sin 0.1V
* 期望: PSS 收敛, drain 基频幅度 < VDD; .hb 自动走 PSS 回退路径

VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.7 SIN(0.7 0.1 1MEG)

* M1: d g s b
M1 d g 0 0 nmos w=1u l=130n

* PTM 130nm 简化 BSIM4 nmos 模型, 通过 file= 指向编译好的 OSDI 库
* 参数集与 tests/test_shooting.cpp 中 bsim4ModelParams() 对齐
.model nmos bsim4va file="models/bsim4.dll"
+ toxe=3e-9 toxp=3e-9
+ vth0=0.5 k1=0.5 k2=0 k3=0
+ dvt0=1 dvt1=2 dvt2=-0.032
+ u0=0.045 ua=-1e-10 ub=0
+ vsat=1.5e5 rdsw=160 nfactor=1.2
+ cgso=0.1e-9 cgdo=0.1e-9 cgbo=0
+ cjs=1e-3 cjd=1e-3 cjsws=1e-10 cjswd=1e-10
+ mjs=0.5 mjd=0.5 mjsws=0.33 mjswd=0.33
+ pbs=0.88 pbd=0.88 pbsws=0.88 pbswd=0.88

.op
.pss freq=1MEG nh=3 pts=32
.hb  freq=1MEG nh=3

.end
