`timescale 1ns/1ps
module stamp #(parameter W=4)(input wire[W-1:0] a,output logic[W-1:0] q);
  function automatic integer remember(input integer x);
    static integer calls=0;
    calls++;return x+calls;
  endfunction
  initial begin q=0;#1;q=remember(a);#2;q=remember(a);end
endmodule
module group #(parameter W=4, FIRST=1, LAST=-1)(input wire[3*W-1:0] a,output wire[3*W-1:0] q);
  for(genvar i=0;i<1;i++)begin:g
    stamp #(.W(W)) s[FIRST:LAST](.a(a),.q(q));
  end
endmodule
module top;
  logic[11:0] a;logic[14:0] b;wire[11:0] qa;wire[14:0] qb;
  group #(.W(4)) g1(a,qa);group #(.W(5)) g2(b,qb);
  initial begin
    a=12'h123;b={5'd1,5'd2,5'd3};#2;
    $display("TRACE generated %h %h",qa,qb);
    if(qa!==12'h234||qb!=={5'd2,5'd3,5'd4})$fatal(1,"per-instance function state");
    #2;$display("TRACE generated %h %h",qa,qb);
    if(qa!==12'h345||qb!=={5'd3,5'd4,5'd5})$fatal(1,"static function isolation");
    $finish;
  end
endmodule
