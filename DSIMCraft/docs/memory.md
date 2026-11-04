# RTL 存储器与文件初始化

M34 已扩展到[静态多维 unpacked 变量数组](multidim-arrays.md)。下文原有单维示例继续适用；当前多维范围和限制以该文档为准。

支持独立 RTL 前端中的一维 unpacked `reg` / `logic` 数组，例如：

```verilog
reg [31:0] mem [0:1023];
assign dout = mem[addr];
always @(posedge clk) if (we) mem[addr] <= #2 din;
initial $readmemh("firmware.hex", mem);
```

支持常量/运行时索引、递增或递减声明及非零下界、标量和多字四态元素；元素的 packed 位/固定范围/固定宽度 `+:`、`-:` 选择和拼接赋值；阻塞、NBA 及已有过程延迟。NBA 在发出时采样地址，阻塞内部 delay 在恢复时求目标地址，RHS 在等待前采样。未知或越界地址读 X、写无效。常量地址直接生成普通信号访问；运行时地址通过只读 ID 表 O(1) 定位，整字写直接进入 `set` / NBA 调度，部分字写复用原有部分赋值路径。

动态读取的编译期依赖包括地址及所有可能元素，支持 `assign`、`always @*`、`always_comb`。常量元素可用于显式事件控制；动态元素显式事件表达式仍不支持。动态写入保守检查所有可能元素的 writer 冲突。独立存储器域接入 `--threads`，元素状态、待提交写入、打印及波形复用已有 checkpoint/predict 回滚机制；这里没有新增自动预测器。

`$readmemh` / `$readmemb` 支持常量字符串文件名、一维数组目标及可选运行时 start/end。文件按运行目录解析，支持空白、`//` / `/* */` 注释、下划线、X/Z 和十六进制 `@` 地址；二进制文件的地址也为十六进制。默认从最小地址递增，显式 start > end 时递减装载。省略 end 时使用最大地址。短数据零扩展，首位为 X/Z 时按四态扩展；超宽数据截断到元素宽度。VCS 对部分超宽文件项会警告并停止装载，本实现的截断行为不保证相同。整个文件通过检查后才发布修改；缺失文件、非法字符、未知/溢出边界、超出选定区间等明确失败。回放要求输入文件内容保持不变。

`--wave-support` 生成的 VCD/DWF 包括每个元素，例如 `mem[3]`，并支持有序/settled 和线程捕获。当前 `$dumpvars` 的数组/元素目标没有扩展；使用 CLI 捕获完整设计。VCS 默认不导出这些数组元素，对照用例用 packed 观察信号显式连接全部元素后比较。

限制：仅一维、非负声明地址，最多 1,048,576 个元素；packed 元素已支持 [unsigned/signed](signed.md)，范围保持 descending 限制。不支持数组端口、unpacked net 数组、数组切片/整数组赋值/聚合初始化、多维数组、动态数组、关联数组、队列或运行时字符串文件名。元素复用现有 Signal 存储，动态敏感依赖按全部元素登记；尚未实现大容量 RAM 的专用紧凑存储与细粒度依赖优化，未证明接近 VCS 的存储器性能。

回归入口：`ctest --test-dir build -R '^rtl_memory$' --output-on-failure`。

默认 signed 的 32 位 `integer/int` 数组及过程块局部一维数组已在 [M13](integer-and-locals.md) 接通；多维/端口/整数组等限制继续适用。
