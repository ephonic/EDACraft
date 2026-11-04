# 已知 RTL 字符串 lexer 缺陷

`same-line.v` 与 `separate-lines.v` 都应输出两行 `TRACE a`、`TRACE b`。当前 dsim 对同一行输入把两个字符串之间的源码一起作为字符串内容；分行输入和 Icarus 两例输出正确。见 `results.json`、各工具日志及生成 C++ 的 display 指令。

原因是原 `verilog.l` 的字符串规则 `\".*?\"` 在 Flex 中仍采用最长匹配。本批 0.7.0 未修改 RTL parser；该失败不计入 42 个通过用例。后续 M2 应修复引号/反斜杠转义匹配并增加同输入 VCS 回归。

复现（输出路径可自选）：

```sh
./build/dsim validation/m3-sequential/known-rtl-string-lexer/same-line.v -o build/string-probe
./build/string-probe
iverilog -g2012 -s top -o build/string-probe.iv validation/m3-sequential/known-rtl-string-lexer/same-line.v
vvp build/string-probe.iv
```
