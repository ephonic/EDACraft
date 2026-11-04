# 多驱动 PORT 回标修正

原437源新VCS对照发现：同一多驱动接收pin先PORT=9、再PORT=3时，VCS仍为9；单驱动则为3。叶作用域和父作用域一致，反向3→9也为9。生产`src/sdf_annotation.cpp`已将PORT纳入既有MAXIMUM MIPD合并，继续复用同一接收通道；没有改runtime、RTL/gate parser、路径字典或波形/并行头文件。多驱动非零ABS之后读回零的既有限制继续明确拒绝。

443文件源`48e19c91e83b4a5ea9f2cc462c9c14cba9b69a2eca67f0ee474e37393c3460c2`已冻结。本地六场景、四后端、24次完整C++等价与144份ordered/settled×VCD/raw/Zstd捕获通过。三个新增场景用原始VCS物理波形核对top.x/top.y及实际私有接收fast.A，共36次信号比较；其余普通未回标输入没有独立波形名，不声称已逐名核对。独立核对见[local-validation.json](local-validation.json)，原始文件含前次oracle访问未导出输入名的失败日志，修正后在新目录完整重跑。

新一轮六组VCS各三次已正常结束0，原始归档`92f7126aaf69045b8fd7cfe92c87018dc281479ab28113380910d5ecabff9560`已下载，18次完整波形、84次物理信号比较及零注解错误/警告独立重算PASS，见[vcs-verification.json](vcs-verification.json)。此修正不解决DEVICE与IOPATH混合状态、VCS相同模块合并后的通配回标范围或primitive DEVICE，原32组失败证据仍完整保留。Linux完整集成待后续，无新性能结论。
