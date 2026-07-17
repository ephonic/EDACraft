* rfsim HB 验证: 正弦驱动 RC 低通
* V1=DC 2V + AC 1V @ 159kHz, R=1k, C=1nF (fc=159kHz)
* HB 应给出: DC 谐波 v(out)=1V, 基频 |v(out)|=0.707

V1 in 0 2 AC 1
R1 in out 1k
C1 out 0 1n

.hb freq=159154.9 nh=3
.print v(out)

.end
