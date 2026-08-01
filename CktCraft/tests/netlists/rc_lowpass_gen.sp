* RC lowpass — 生成模型 cap_linear (VA ddt) 替代内置 C
Vin in 0 PULSE(0 1 0 1n 1n 10m 20m)
R1  in out 1k
D1  out 0 cap_linear
.model cap_linear cap_linear generated=1 c0=1e-6
.tran 0.1m 5m
.print v(in) v(out)
.end
