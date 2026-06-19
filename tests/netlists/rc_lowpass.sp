* rfsim AC 验证: RC 低通滤波器
* H(jw) = 1/(1+jwRC), fc = 1/(2*pi*1k*1u) = 159.15 Hz

Vin in 0 0 AC 1
R1 in out 1k
C1 out 0 1u

.ac dec 10 1 100k
.print v(out)

.end
