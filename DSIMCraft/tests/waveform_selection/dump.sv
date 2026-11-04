`timescale 1ps/1ps
module child;
  logic [7:0] q;
  initial begin q=1;#1;q=2;#1;q=3;#1;q=4;#1;q=5;#1;q=6;#1;q=7;end
endmodule
module top;
  logic flag;
  child u();child v();
  initial begin
    flag=0;$dumpvars(0,top);
    #1;$dumpall;#1;$dumpoff;flag=1;
    #1;$dumpon;#1;$dumpall;
    #4;$display("TRACE dump complete");$finish;
  end
endmodule
