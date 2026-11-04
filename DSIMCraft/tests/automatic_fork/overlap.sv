`timescale 1ns/1ps
module top;
integer issued=0,q=0,done=0,k=0;
task automatic work();
 integer tag=++issued;
 integer data[0:1];
 reg [95:0] wide;
 bit [7:0] clean;
 begin
  data[0]=tag; data[1]=tag*10;
  wide={32'hdeadbeef,32'h12345678,32'h9abcdef0};
  clean=8'bx101z011;
  wide[39:32]=tag;
  #(7-tag);
  if(wide[95:40]!==56'hdeadbeef123456||wide[39:32]!==tag[7:0]||wide[31:0]!==32'h9abcdef0||clean!==8'h53)$fatal(1,"packed frame");
  q+=data[0]+data[1];done++;
 end
endtask
initial begin
 for(k=0;k<6;k++)fork work();join_none
 wait fork;
 $display("TRACE overlap %0d %0d %0d",issued,q,done);
 if(issued!=6||q!=231||done!=6)$fatal(1,"automatic alias");
 $finish;
end
endmodule
