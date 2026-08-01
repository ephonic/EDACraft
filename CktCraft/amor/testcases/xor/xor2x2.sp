*.xor2x2
M0 net29 net21 net37 VDD MP l=0.18u w=1.4u
M1 net29 A net38 VDD MP l=0.18u w=1.4u
M2 net29 A net37 VSS MN l=0.18u w=0.92u
M3 net29 net21 net38 VSS MN l=0.18u w=0.92u
M4 Y net29 VSS VSS MN l=0.18u w=1.2u
M5 VDD net29 Y VDD MP l=0.18u w=1.76u
M6 net21 A VSS VSS MN l=0.18u w=0.38u
M7 VDD A net21 VDD MP l=0.18u w=0.56u
M8 net37 net38 VSS VSS MN l=0.18u w=0.92u
M9 VDD net38 net37 VDD MP l=0.18u w=1.4u
M10 net38 B VSS VSS MN l=0.18u w=2.52u
M11 VDD B net38 VDD MP l=0.18u w=3.82u


cl Y VSS 1p

VGND VSS 0 0

VDD VDD VSS 1.8
*V1 A GND sin 0.9 0.9 1e8 0 0 180
*V2 B GND sin 0.9 0.9 2e8 0 0 0
V1 A VSS pulse 0 1.8v 5n 0.1n 0.1n 10n 20n
*V2 B GND pulse 0 1.8v 5n 0.1n 0.1n 20n 40n
V2 B VSS 0

.inc 'model.inc'

*.option mordump=xor.mat table

.op
.option post
.tran 0.1n 40n
.probe tran V(Y)
.print tran V(Y)
.end
