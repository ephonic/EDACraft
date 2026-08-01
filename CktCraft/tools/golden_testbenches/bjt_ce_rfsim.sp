* BJT (MEXTRAM 505) Common-Emitter DC Test
VCC vcc 0 3.0
RC  vcc c  10k
VB  b   0 0.7
VE  e   0 0.0

Q1 c b e 0 bjt_npn

.model bjt_npn bjt505va generated=1
+ type=1
+ is=1e-16
+ bf=100
+ vaf=50
+ re=1
+ rc=10
+ rb=100
+ tref=25

.dc VB 0.5 0.9 0.02
.print v(c) i(VCC)
.end
