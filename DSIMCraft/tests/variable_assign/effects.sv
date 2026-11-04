`timescale 1ns/1ps
module shape #(parameter W=4)(input [W-1:0]d,output logic[W-1:0]q);
 assign q=d+1;
endmodule
module top;
 logic [7:0] d=0;
 integer calls=0;
 wire [3:0] hi;
 logic [3:0] lo;
 logic [3:0] q4;
 logic [8:0] q9;
 function automatic [7:0] get(input [7:0]x);
  begin calls++;return x+8'h12;end
 endfunction
 assign {hi,lo}=get(d);
 shape #(4) a(d[3:0],q4);
 shape #(9) b({1'b0,d},q9);
 initial begin
  #2 $display("TRACE effects %h %h %0d %h %h",hi,lo,calls,q4,q9);
  if(hi!==1||lo!==2||calls!==1||q4!==1||q9!==1)$fatal(1,"effects once");
  d=8'h2a;
  #2 $display("TRACE effects %h %h %0d %h %h",hi,lo,calls,q4,q9);
  if(hi!==3||lo!==12||calls!==2||q4!==11||q9!==43)$fatal(1,"effects update");
  d<=8'hff;
  #2 $display("TRACE effects %h %h %0d %h %h",hi,lo,calls,q4,q9);
  if(hi!==1||lo!==1||calls!==3||q4!==0||q9!==256)$fatal(1,"effects final");
  $finish;
 end
endmodule
