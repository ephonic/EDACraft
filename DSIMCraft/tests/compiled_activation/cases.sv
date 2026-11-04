`timescale 1ns/1ps
module top;
logic clk=0;
logic signed [3:0] sel=0;
logic [7:0] a=5,b=9,q,decoded,latch_value;
integer taken;
always #5 clk=~clk;
always_comb begin
 decoded=a;
 unique case(sel)
  0,1: decoded=a+b;
  2: begin
   case(a[1:0])
    0: decoded=b;
    1: decoded=~b;
    default: decoded=a^b;
   endcase
  end
  4'shf: decoded=8'hff;
  default: decoded=b;
 endcase
end
always_latch begin
 case(sel)
  0: latch_value=a;
  2: latch_value=decoded;
 endcase
end
always @(posedge clk) begin
 case(sel)
  0: q<=decoded;
  1,1: q<=latch_value;
  2: if(a[0]) q<=a; else q<=b;
  4'shf: q<=8'hff;
  default: q<=8'hxx;
 endcase
end
// Duplicate branches exercise diagnostic order as well as first-match rules.
always_comb begin
 unique case(sel)
  3: taken=1;
  3: taken=2;
  default: taken=0;
 endcase
end
initial begin
 #1;$display("TRACE cases %h %h %h %0d",decoded,latch_value,q,taken);
 #5;sel=1;
 #10;sel=2;a=4;
 #10;a=5;
 #10;sel=-1;
 #10;sel=4'bx001;
 #10;sel=4'bz001;
 #10;sel=3;
 #10;sel=7;
 #10;sel=0;a=8'hxx;
 #10;$display("TRACE cases %h %h %h %0d",decoded,latch_value,q,taken);$finish;
end
endmodule
