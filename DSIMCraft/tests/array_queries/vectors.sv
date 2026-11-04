`timescale 1ns/1ps
module top;
logic[3:0] value;logic control;int i=0,j=0,temp=0;
int zeroes=0,ones=0,exes=0,zees=0,selected=0;
initial begin
 for(i=0;i<256;i++)begin
  temp=i;
  for(j=0;j<4;j++)begin
   case(temp%4)
    0:value[j]=1'b0;1:value[j]=1'b1;2:value[j]=1'bx;3:value[j]=1'bz;
   endcase
   temp=temp/4;
  end
  zeroes=0;ones=0;exes=0;zees=0;
  for(j=0;j<4;j++)begin
   if(value[j]===1'b0)zeroes++;
   if(value[j]===1'b1)ones++;
   if(value[j]===1'bx)exes++;
   if(value[j]===1'bz)zees++;
  end
  if($countbits(value,1'b0)!=zeroes||$countbits(value,1'b1)!=ones||$countbits(value,1'bx)!=exes||$countbits(value,1'bz)!=zees)$fatal(1,"individual states %0d",i);
  if($countbits(value,1'b1,1'b0)!=ones+zeroes||$countbits(value,1'bx,1'bz,1'bx)!=exes+zees||$countbits(value,1'b0,1'b1,1'bx,1'bz)!=4)$fatal(1,"sets %0d",i);
  control=value[0];selected=0;
  for(j=0;j<4;j++)if(value[j]===control)selected++;
  if($countbits(value,control,control)!=selected)$fatal(1,"runtime controls %0d",i);
  #1;
 end
 $display("TRACE vectors %0d",i);
end
endmodule
