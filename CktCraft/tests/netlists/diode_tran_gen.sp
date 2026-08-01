* diode_va 瞬态 (含 cj0 结电容) — generated 模型
Vin in 0 SIN(0 1 1MEG)
R1  in a 1k
D1  a  0 0 diode_va
.model diode_va diode_va generated=1 rs=0.1 cj0=1e-11
.tran 1e-8 2e-6
.print v(in) v(a)
.end
