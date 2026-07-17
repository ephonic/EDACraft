* rfsim DC 扫描验证: 分压器传输特性
* 扫 V1 从 0 到 5V，观察分压节点

V1 in 0 0
R1 in out 2k
R2 out 0 3k

.dc V1 0 5 1
.print v(out)

.end
