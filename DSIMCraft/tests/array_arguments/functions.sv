`timescale 1ns/1ps
module top;
integer a[2:1],b[4:5],r=0,out=0;
function automatic integer total(input integer x[7:8]=a);
 integer sum=0;foreach(x[i])sum+=x[i];return sum+$size(x)-2;
endfunction
function automatic integer mix(input integer x[0:1],output integer y[2:1],inout integer z[0:1]);
 y[2]=x[0]+1;y[1]=x[1]+2;z[0]+=x[0];z[1]+=x[1];return y[2]+y[1];
endfunction
function automatic integer combine(ref integer x[0:1],ref integer y[4:5]);
 x[0]++;y[5]+=2;return x[0]+y[5];
endfunction
initial begin
 a[2]=3;a[1]=4;b[4]=10;b[5]=20;
 r=total();r+=mix(.z(a),.y(b),.x(a));r+=combine(a,a);out=total(.x());
 $display("TRACE functions %0d %0d %0d %0d %0d %0d",a[2],a[1],b[4],b[5],r,out);
 if(a[2]!=7||a[1]!=10||b[4]!=4||b[5]!=6||r!=34||out!=17)$fatal(1,"array function aliases and defaults");
end
endmodule
