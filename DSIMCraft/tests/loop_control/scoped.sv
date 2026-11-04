`timescale 1ns/1ps
module top;
integer seed=2,total=0,hits=0;
integer i=99;
initial begin : worker
 repeat(2)begin
  for(int i=seed,j=seed+3;i<seed+4;i++,j--)begin
   #1;
   for(integer k=0;k<4;++k)begin
    if(k==1)continue;
    if(k==3)break;
    total=total+i+j+k;
   end
   if(i==seed+1)continue;
   hits++;
  end
  $display("TRACE scoped %0d %0d %0d %0d",seed,total,hits,i);
  seed=seed+3;
 end
 repeat(2)begin
  for(int scratch;;)begin
   $display("TRACE fresh %h",scratch);
   scratch=7;
   break;
  end
 end
 $finish;
end
endmodule
