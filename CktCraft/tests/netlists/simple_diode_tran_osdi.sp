* simple_diode 瞬态 — openvaf dll (2 端子无内部节点)
Vin in 0 SIN(0 1 1MEG)
R1  in a 1k
D1  a  0 simple_diode
.model simple_diode simple_diode file="G:/vibe-codeing/simulator/CktCraft/models/simple_diode.dll"
.tran 1e-8 2e-6
.print v(in) v(a)
.end
