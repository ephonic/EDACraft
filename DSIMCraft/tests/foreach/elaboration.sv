`timescale 1ns/1ps
module child #(parameter W=5, L=1)(input logic[W-1:0] data,output integer total);
  logic[1:0] values[L:L+1];
  always_comb begin
    total=0;foreach(data[i]) if(data[i])total+=i;
  end
  initial foreach(values[i]) values[i]=i;
endmodule
module top;
  logic[4:0] a=0;logic[8:0] b=0;
  wire[31:0] x,y;
  child #(5,2) u(a,x);child #(9,4) v(b,y);
  generate for(genvar g=0;g<2;g=g+1)begin:lanes
    logic[2:0] bits=0;integer sum=0;
    initial begin foreach(bits[k])begin #1;sum+=k+g;end
      if(sum!=3+g*3)$fatal(1,"generate loop clone");end
  end endgenerate
  initial begin
    #1;a=5'b10101;b=9'b100010001;
    #1;if(x!=6 || y!=12)$fatal(1,"parameter clone");
    #2;
    $display("TRACE elaboration %0d %0d",x,y);
  end
endmodule
