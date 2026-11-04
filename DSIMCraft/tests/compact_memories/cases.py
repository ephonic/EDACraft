"""Fixed arrays exercise compact storage, without C910-specific assumptions."""
CASES = {
 'large': r'''module top;
  reg [7:0] memory [7:2097158];
  reg clk=0;
  wire [7:0] observed=memory[2097158];
  integer index;
  initial begin
    $display("TRACE defaults=%b/%b size=%0d",memory[7],memory[2097158],$size(memory));
    memory[7]=8'ha5;memory[2097158]=8'h3c;
    index=2097158; memory[index][7:4] <= #2 4'hd;
    memory[index][3:0] <= #2 4'h2;
    memory[-1] <= 8'hff; memory[2097159] <= 8'hff;
    index=8; memory[index] <= @(posedge clk) 8'h69;
    index=2097158;
    memory[index] <= @(posedge clk) 8'hb7;
    #1; $display("TRACE before=%h/%h/%h",memory[7],memory[8],observed);
    #2; $display("TRACE delayed=%h",observed);clk=1;
    #1; $display("TRACE event=%h/%h",memory[8],observed);
    $display("TRACE invalid=%b/%b",memory[-1],memory[2097159]);$finish;
  end
endmodule
''',
 'file-and-shape': r'''module top;
  reg [15:0] memory [4102:7];
  bit [7:0] bytes [0:4095];
  reg [143:0] matrix [1:2][5:2052];
  initial begin
    $display("TRACE shape=%0d/%0d/%0d/%0d",$left(memory),$right(memory),$size(memory),$size(matrix,2));
    $readmemh("input.hex",memory,9,7);
    $writememh("roundtrip.hex",memory,9,7);
    memory[7]=0;memory[8]=0;memory[9]=0;
    $readmemh("roundtrip.hex",memory,9,7);
    matrix[1][5]=144'h123456789abcdef00112233445566778899;
    matrix[2][2052]=144'hfedcba9876543210aabbccddeeff00112233;
    matrix[2][2052][143:128] <= 16'habcd;
    bytes[4095]=8'hxz;
    #1; $display("TRACE file=%h/%h/%h zero=%h",memory[7],memory[8],memory[9],bytes[4095]);
    $display("TRACE matrix=%h/%h",matrix[1][5],matrix[2][2052]);$finish;
  end
endmodule
'''
}
EXPECTED = {
 'large':['TRACE defaults=xxxxxxxx/xxxxxxxx size=2097152','TRACE before=a5/xx/3c','TRACE delayed=d2','TRACE event=69/b7','TRACE invalid=xxxxxxxx/xxxxxxxx'],
 'file-and-shape':['TRACE shape=4102/7/4096/2048','TRACE file=xxxx/55aa/1234 zero=00','TRACE matrix=0123456789abcdef00112233445566778899/abcdba9876543210aabbccddeeff00112233']
}
def make(root):
 root.mkdir(parents=True,exist_ok=True)
 for name,source in CASES.items():
  work=root/name;work.mkdir(exist_ok=True);(work/'tb.sv').write_text(source)
  (work/'input.hex').write_text('@9 1234 55aa xxxx\n')
