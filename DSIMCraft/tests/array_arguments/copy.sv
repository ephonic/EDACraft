`timescale 1ns/1ps
module top;
 integer a[2:1],b[0:1],c[0:1],r=0;
 function automatic integer total(input integer x[7:8]);return x[7]+x[8];endfunction
 task automatic copy(input integer x[4:5],output integer y[8:7],inout integer z[0:1]);
  #2;y[8]=x[4];y[7]=x[5];z[0]+=10;z[1]+=20;
 endtask
 initial begin
  a[2]=3;a[1]=4;b[0]=5;b[1]=6;c[0]=0;c[1]=0;
  r=total(a);fork copy(a,c,b);begin #1;a[2]=99;b[0]=100;end join
  $display("TRACE copy %0d %0d %0d %0d %0d",r,c[0],c[1],b[0],b[1]);
  if(r!=7||c[0]!=3||c[1]!=4||b[0]!=15||b[1]!=26)$fatal(1,"array copy timing and order");
 end
endmodule
