# 通用文本文件 I/O

M103 为编译式 RTL 仿真接入以下接口。RTL 与门级网表 parser 继续分离。

| 接口 | 本轮范围 |
| --- | --- |
| `$fopen(path)` | 创建写入 MCD，可按位或组合多个通道及 stdout 通道 1 |
| `$fopen(path, mode)` | 返回 FD；支持 `r/w/a`、`r+/w+/a+` 及对应 `b` 拼写；失败返回 0 |
| `$fwrite/$fdisplay` | FD/MCD 格式化写入；后者追加换行；动态文件名和格式 |
| `$fclose/$fflush` | 关闭指定文件/通道；无实参 fflush 刷新全部已提交输出 |
| `$fgetc/$ungetc/$feof` | 无符号字节、EOF 返回 -1、字符回推和 EOF 状态 |
| `$fgets` | 写回 string 或 packed 变量/元素/片选，返回实际读入字节数 |
| `$ftell/$fseek/$rewind` | 字节位置；seek 支持起点/当前位置/末尾（0/1/2），失败返回 -1 |

```systemverilog
int fd, count, status;
string path="stimulus.txt", line;
initial begin
  fd=$fopen(path,"r");
  if (!fd) $fatal(1,"cannot open %s",path);
  count=$fgets(line,fd);
  while (count>0) begin
    $display("%s",line);
    count=$fgets(line,fd);
  end
  $fclose(fd);
end
```

packed 缓冲区每次最多读取 `floor($bits(target)/8)` 字节，包含换行。遇到嵌入 NUL 时 packed 保留该字节，string 内容在首个 NUL 处截断，但返回值仍计入全部读入字节。EOF 时 string 清空，packed 目标保留；没有 packed 写回就不求值目标下标，因而 `$fgets(a[i++],fd)` 到 EOF 后不递增 i。最后一行没有换行时，读取越过结尾会同时设置 EOF；容量已满时不额外探测 EOF。ungetc 成功返回 0 并清除 EOF；回推队列、游标与 EOF 均属于仿真状态。`a+` 初始读取位置为起点，每次写入仍定位到末尾。

格式化沿用 [M102 格式范围](testbench-io.md)：`%b/%d/%h/%x/%o/%t/%s/%c/%m`、十进制字段宽度、`%%`，支持宽值和动态格式。fwrite/fdisplay 当前要求 descriptor 后提供格式参数。FD 是不透明句柄；不能依赖其数值或与 MCD 混用。stdin 交互读取不支持；stdout/stderr 可通过标准 FD 写入。

## 预测、分区及文件副作用

每个 Sim 保存文件表、位置、回推及按需复制的字节内容。检查点共享不可变内容，首次修改时复制；常规追加只更新增量，避免每次复制整份文件。推测阶段记录拥有自身参数的有序写入/截断/刷新动作，读取可见同一推测分支的写入。拒绝预测后恢复文件状态并丢弃外部动作；接受后按顺序只提交一次。提交时发生 OS 错误会报告失败，禁止自动重放已提交的副作用。普通手动 checkpoint/restore 只恢复内部状态，不能撤回已经提交的真实文件写入。

所有通用文件操作以及内存文件操作通过副作用依赖合并到同一执行域，包含声明初始化和子程序调用。其余独立计算域仍可并行。文件内容也接入 `$readmemh/$writememh` 的推测可见性；既有内存文件任务仍要求常量路径。

当前针对可由内存保存的普通文件；输入按文件载入，关闭后缓存仍保留。测试/预测期间假定外部进程不修改输入、路径或权限；不合并符号/硬链接别名，不支持 FIFO、管道、设备或交互 stdin。推测 fopen 不实际创建文件，只检查可见路径与权限，最终 OS 打开失败在提交时报告。超大文件的流式缓存、完整 OS 错误查询和交互文件同步仍待实现。

`$fscanf/$sscanf` 的 M104 支持范围见 [格式化扫描](formatted-scan.md)。`$fread/$ferror`、fdisplayh 等格式任务族、实数/浮点和完整格式族尚未接入。未支持的模式/格式、无效或含 X/Z 的 descriptor/offset，以及对只读句柄写入会明确报错退出；这些错误路径不宣称与 VCS 的警告/返回值完全一致。

同源 VCS、文件字节、完整数值波形、实际双分区、成功提交/失败回放及生成程序 sanitizer 证据见 [M103](../validation/m103-file-io/README.md)。本轮没有重新测量性能。
