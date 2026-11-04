"""Small, design-independent reproductions of the C910 integration blockers."""
CASES = {
    'module-value-namespace': '''module counter #(parameter START=1);
  reg [31:0] counter=START;
  initial begin #1; counter=counter+1; end
endmodule
module top;
  counter #(7) a(); counter #(20) b();
  initial begin #2; $display("TRACE namespace=%0d/%0d",a.counter,b.counter);$finish;end
endmodule
''',
    'implicit-assignment': '''module top;
  reg enable=0;
  assign create_en=enable && 1'b1;
  initial begin #1; $display("TRACE implicit=%b bits=%0d",create_en,$bits(create_en));
    enable=1; #1; $display("TRACE implicit=%b",create_en);$finish;end
endmodule
''',
    'nested-generate': '''module top;
  wire [599:0] value;
  for(genvar i=0;i<300;i=i+1) begin: outer
    for(genvar j=0;j<2;j=j+1) begin: inner
      if((i+j)%3==0) begin: yes
        assign value[2*i+j]=1'b1;
      end else begin: no
        assign value[2*i+j]=1'b0;
      end
    end
  end
  initial begin #1; $display("TRACE generate=%b",value);$finish;end
endmodule
''',
    'forward-constant-function': '''module counter #(parameter N=32)(result);
  parameter WIDTH=clog2(N-1);
  output [WIDTH-1:0] result;
  function automatic integer clog2(input integer a);
    begin for(clog2=0;a>0;clog2=clog2+1) a=a>>>1; end
  endfunction
  assign result={WIDTH{1'b1}};
endmodule
module top;
  wire [4:0] a; wire [7:0] b;
  counter #(32) x(a); counter #(256) y(b);
  initial begin #1; $display("TRACE constfunc=%h/%h widths=%0d/%0d",a,b,$bits(a),$bits(b)); $finish; end
endmodule
''',
    'implicit-terminal': '''module driver(output [3:0] wide, output flag);
  assign wide=4'ha; assign flag=1'b1;
endmodule
module top;
  wire [3:0] later;
  driver dut(later,implicit_wire);
  initial begin #1; $display("TRACE terminal=%h/%b bits=%0d",later,implicit_wire,$bits(implicit_wire)); $finish; end
endmodule
''',
    'shared-child': '''module leaf; reg [7:0] mem [0:3]; endmodule
module unused; leaf u(); endmodule
module unused_cycle; unused_cycle u(); endmodule
module top;
  initial begin #1; a.mem[2]=8'hac; b.mem[2]=8'h35; #1;
    $display("TRACE shared=%h/%h",a.mem[2],b.mem[2]); $finish; end
  leaf a(); leaf b();
endmodule
''',
    'static-data': '''module holder #(parameter P=1);
  static integer count=P;
  static reg [7:0] bytes [0:1];
endmodule
module top;
  initial begin #1; a.count=a.count+2; b.count=b.count+3;
    a.bytes[1]=8'ha5; b.bytes[1]=8'h5a; #1;
    $display("TRACE static=%0d/%0d bytes=%h/%h",a.count,b.count,a.bytes[1],b.bytes[1]); $finish; end
  holder #(7) a(); holder #(20) b();
endmodule
''',
    'nested-replication': '''module top;
  parameter N=10;
  reg [3:0] a=4'b10xz;
  wire [9:0] b={{N{1'b1}}};
  wire [11:0] c={1'b0,{N{1'bz}},1'b1};
  wire [31:0] d={2{{2{a}},{2{a}}}};
  wire [143:0] e={{144{1'b1}}};
  initial begin #1; $display("TRACE concat=%b/%b/%b/%h",b,c,d,e);
    a=4'b0110; #1; $display("TRACE changed=%b",d); $finish; end
endmodule
''',
    'root-hierarchy': '''module ram;
  reg [15:0] mem [0:7] /* synthesis syn_ramstyle = "no_rw_check" */;
endmodule
module watcher;
  initial begin #2; $display("TRACE sibling=%h/%h",top.left.mem[3],top.right.mem[3]); end
endmodule
module top;
  initial begin #1; top.left.mem[3]=16'hcafe; top.right.mem[3]=16'h1234;
    top.left.mem[3][7:0]=8'ha5;
    #2; $display("TRACE root=%h/%h",top.left.mem[3],top.right.mem[3]); $finish; end
  watcher monitor(); ram left(); ram right();
endmodule
''',
}

EXPECTED = {
    'module-value-namespace': ['TRACE namespace=8/21'],
    'implicit-assignment': ['TRACE implicit=0 bits=1','TRACE implicit=1'],
    'nested-generate': ['TRACE generate='+''.join(str(int((i+j)%3==0)) for i in range(299,-1,-1) for j in (1,0))],
    'forward-constant-function': ['TRACE constfunc=1f/ff widths=5/8'],
    'implicit-terminal': ['TRACE terminal=a/1 bits=1'],
    'shared-child': ['TRACE shared=ac/35'],
    'static-data': ['TRACE static=9/23 bytes=a5/5a'],
    'nested-replication': [
        'TRACE concat=1111111111/0zzzzzzzzzz1/'+'10xz'*8+'/'+'f'*36,
        'TRACE changed='+'0110'*8,
    ],
    'root-hierarchy': ['TRACE sibling=caa5/1234','TRACE root=caa5/1234'],
}


def make(out):
    out.mkdir(parents=True, exist_ok=True)
    for name, source in CASES.items():
        work = out/name
        work.mkdir(exist_ok=True)
        (work/'tb.sv').write_text(source)
