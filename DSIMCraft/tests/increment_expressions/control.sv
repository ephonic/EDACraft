`timescale 1ns/1ps
module top;
integer i=0,j=0,k=0,m=0,result=0,total=0;
reg unknown=1'bx;
initial begin
 #1;result=0&&(i++);result=1||(j++);
 $display("TRACE short %0d %0d %0d",i,j,result);
 result=1?(++i):(++j);result=0?(++i):(++j);
 result=unknown?(k++):(m++);
 if(i++==1)result+=10;
 while(j++<3)#1;
 $display("TRACE control %0d %0d %0d %0d %0d",i,j,k,m,result);
 repeat(i++)#1;
 for(j=0;j++<3;)total+=j;
 $display("TRACE loops %0d %0d %0d",i,j,total);
 result=1'bx&&(i++);result=1'bx||(j++);
 $display("TRACE unknown %0d %0d %0d",i,j,result);
 #1;$finish;
end
endmodule
