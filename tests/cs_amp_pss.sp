* rfsim PSS waveform test — common source BSIM4 amplifier
* 1MHz sine input, PSS shooting analysis

.model nch bsim4 (level=14 w=1u l=130n vth0=0.5 kp=50u)

vdd 1 0 dc 1.5
vin 2 0 sin(0.85 0.05 1meg)

rd 1 3 5k
m1 3 2 0 0 nch w=1u l=130n

.pss freq=1meg nh=5 pts=64
.print v(3)
