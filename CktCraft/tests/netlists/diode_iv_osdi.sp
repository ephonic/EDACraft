* Diode I-V sweep — openvaf/OSDI baseline (absolute dll path for CLI runs)
* Pair of diode_iv_gen.sp for generated-vs-openvaf comparison.

VDD vdd 0 5
R1 vdd a 1k
D1 a 0 simple_diode

.model simple_diode simple_diode file="G:\vibe-codeing\simulator\CktCraft\models\simple_diode.dll"

.dc VDD 0 5 0.05
.print v(a)
.end
