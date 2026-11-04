`timescale 1ns/1ps
module top;
integer a=0,b=0,ea=0,eb=0,i=0,j=0;
logic ma=0,mb=0;
initial for(i=0;i<5;i++)begin #3 a=i+1;ma=a inside {[2:4]};if(ma!==((i+1>=2)&&(i+1<=4)))ea++;end
initial for(j=0;j<5;j++)begin #4 b=j+10;mb=b==?4'b11??;if(mb!==((j+10>=12)&&(j+10<=15)))eb++;end
endmodule
