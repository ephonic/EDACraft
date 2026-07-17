* Full PDK end-to-end: TSMC 28nm HVPDK, TT corner, level=54 BSIM4
* 验证：.lib corner 嵌套选择 + level=54 路由 + 统计变量表达式求值 完整链路。
* 用法: rfsim -L models tests/netlists/pdk_full_e2e_test.sp
*   （从仓库根运行；.lib './...' 路径相对 pdk/models/hspice/）
VDD vdd 0 1.8
RD  vdd d  10k
VG  g   0  1.0
M1 d g 0 0 nch_hv18 w=2u l=180n
* 加载 PDK 顶层库，选 TOP_TT corner（递归 .lib 嵌套）
.lib 'pdk/models/hspice/toplevel.l' TOP_TT
.op
.print v(d) i(vdd)
.end
