`timescale 1ns/1ps
module top;
integer a[1:0][4:3],source[7:6],index=1,source_index=1,seen=0;
function automatic integer pick();seen++;return source_index;endfunction
task automatic update(input integer x[],inout integer y[]);
 foreach(y[i])y[i]+=x[i];#2;y[0]+=10;
endtask
initial begin
 a[1][4]=1;a[1][3]=2;a[0][4]=100;a[0][3]=200;
 source[7]=3;source[6]=4;
 fork update(a[pick()],a[index]);begin #1;index=0;source_index=0;end join
 $display("TRACE elements %0d %0d %0d %0d %0d",a[1][4],a[1][3],a[0][4],a[0][3],seen);
 if(a[1][4]!=1||a[1][3]!=2||a[0][4]!=12||a[0][3]!=4||seen!=1)$fatal(1,"unsized dynamic prefix copyout");
end
endmodule
