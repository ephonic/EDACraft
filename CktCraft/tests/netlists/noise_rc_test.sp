* Noise analysis test: resistor thermal noise through RC low-pass
* R=1k 的热噪声经 RC 低通到输出节点（node 2 = out）
* 低频时噪声 ~4kTR，高频被 RC 滤波衰减
Vin in 0 0
R1  in out 1k
C1  out 0   1u
.noise v(2) 1 1MEG 20
.end
