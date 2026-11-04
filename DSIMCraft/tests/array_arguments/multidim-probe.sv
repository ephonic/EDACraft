`timescale 1ns/1ps
module top;
integer a[2][2],b[2][2],result=0;
task automatic update(ref integer x[3:2][8:7],output integer y[2][2]);
 foreach(x[i,j])x[i][j]+=i*10+j;
 y=x;
endtask
function automatic integer sum(input integer x[2][2]);
 integer total=0;foreach(x[i,j])total+=x[i][j];return total+$bits(x)-128;
endfunction
initial begin
 a[0][0]=1;a[0][1]=2;a[1][0]=3;a[1][1]=4;
 update(a,b);result=sum(b);
 $display("TRACE multidim %0d %0d %0d %0d %0d",a[0][0],a[0][1],a[1][0],a[1][1],result);
 if(a[0][0]!=39||a[0][1]!=39||a[1][0]!=31||a[1][1]!=31||result!=140)$fatal(1,"multidimensional formal mapping");
end
endmodule
