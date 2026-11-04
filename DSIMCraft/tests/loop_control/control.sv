`timescale 1ns/1ps
module top;
integer i,j,sum,hits;
initial begin
 sum=0;hits=0;
 for(i=0,j=9;i<7;i++,--j)begin
  #1;
  if(i==2)continue;
  case(i)
   5:break;
   default:sum=sum+i;
  endcase
  hits++;
 end
 $display("TRACE for %0d %0d %0d %0d",i,j,sum,hits);
 i=0;sum=0;
 while(i<6)begin
  ++i;#1;
  if(i==2)continue;
  if(i==5)break;
  sum=sum+i;
 end
 $display("TRACE while %0d %0d",i,sum);
 i=0;sum=0;
 do begin
  i++;#1;
  if(i<3)continue;
  sum=sum+i;
 end while(i<4);
 $display("TRACE do %0d %0d",i,sum);
 i=0;sum=0;
 repeat(5)begin
  i++;#1;
  if(i==2)continue;
  sum=sum+i;
 end
 $display("TRACE repeat %0d %0d",i,sum);
 i=0;
 forever begin
  #1;i++;
  if(i==2)continue;
  if(i==4)break;
 end
 $display("TRACE forever %0d",i);
 for(;;)begin
  #1;
  if(i==6)break;
  i++;
 end
 $display("TRACE empty %0d",i);
 $finish;
end
endmodule
