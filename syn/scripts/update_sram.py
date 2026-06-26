import re

# 读取文件内容
with open('../rtl/Module_instance.v', 'r') as file:
    content = file.read()

# 定义替换的正则表达式和替换内容
pattern = re.compile(r'^ *TS1N28HPCPHVTB128X96M4SWBASO instr_mem[\s\S]*?;', re.MULTILINE)
# 输出匹配到的pattern
print(pattern.findall(content))
replacement = '''  
  TS1N28HPCPHVTB128X96M4SWBASO instr_mem(
    .CLK(sys_clk),
    .CEB(CS_0),
    .WEB(flag_0),
    .A(pc_addr),
    .D(MOSI_out),
    .BWEB(96'h0),
    .Q(rom_data),
    .AM(7'h0),
    .DM(96'h0),
    .BWEBM(96'hFFFF_FFFF_FFFF),
    .BIST(1'b0),
    .CEBM(1'b1),
    .WEBM(1'b1),
    .AWT(1'b0),
    .SLP(1'b0),
    .SD(1'b0)
  );
'''

# 执行替换操作
new_content = pattern.sub(replacement, content)

# 将替换后的内容写回文件
with open('../rtl/Module_instance_new.v', 'w') as file:
    file.write(new_content)