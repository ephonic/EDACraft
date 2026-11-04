`timescale 1ps/1ps
module nested;
  logic [7:0] count;
  initial begin count=3;#2;count=8'hxz;#2;count=9;#2;count=8'hzz;end
endmodule
module branch #(parameter int ID=1);
  logic [128:0] data;
  wire [128:0] alias_data=data;
  logic [7:0] mem[0:1];
  logic \escaped.name[0] ;
  nested inner();
  initial begin
    data=ID;mem[0]=ID;mem[1]=ID+1;\escaped.name[0] =0;
    #1;data=129'h100000000000000000000000000000001+ID;
    #0;data=129'h100000000000000000000000000000003+ID;
    #1;mem[0]=8'hxz;\escaped.name[0] =1;
    #1;data=129'bx;
    #1;data=129'bz;mem[1]=8'hzz;
    #2;data=ID+9;
  end
endmodule
module top;
  logic outside;
  branch #(1) u();branch #(2) v();
  initial begin outside=0;#3;outside=1;#5;$display("TRACE scope complete");$finish;end
endmodule
