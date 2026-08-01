* simple_diode 瞬态 — generated
Vin in 0 SIN(0 1 1MEG)
R1  in a 1k
D1  a  0 simple_diode
.model simple_diode simple_diode generated=1
.tran 1e-8 2e-6
.print v(in) v(a)
.end
