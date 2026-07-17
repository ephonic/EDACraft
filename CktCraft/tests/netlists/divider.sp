* rfsim DC 工作点验证: 电阻分压器 + 电流源
* 纯线性电路，不依赖 OSDI 模型库

V1 in 0 5.0
R1 in mid 2k
R2 mid 0 3k
I1 mid 0 1m

.op
.print v(in) v(mid) i(v1)

.end
