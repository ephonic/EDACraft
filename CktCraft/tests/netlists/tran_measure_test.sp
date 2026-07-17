* Transient + .measure test: RC low-pass, measure final value / max / avg / rise time
Vin in 0 PULSE(0 1 0 1n 1n 10m 20m)
R1  in out 1k
C1  out 0   1u
.tran 0.1m 5m
* 测量：out 的最大值、平均值、RMS、1V 时刻（首升穿越 0.5V 的时间）
.measure tran vmax max v(out) from=0 to=5m
.measure tran vavg avg v(out) from=0 to=5m
.measure tran vrms rms v(out) from=0 to=5m
.measure tran trise when v(out)=0.5 rise=1 from=0 to=5m
.end
