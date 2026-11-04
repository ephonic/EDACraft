`timescale 1ns/1ps
module top;
int result;byte small_value;longint large_value;bit[79:0] wide;integer four;
function byte f(input byte x);byte local_value;begin local_value=x+1;return local_value;end endfunction
function shortint unsigned g(input shortint unsigned x);begin return x/3;end endfunction
function int h(input int x);begin return x/3;end endfunction
function longint unsigned k(input longint unsigned x);begin return x+1;end endfunction
function bit[79:0] mask(input bit[79:0] x);begin return x;end endfunction
function bit one(input bit x);begin return x;end endfunction
task update(input byte x,output shortint q,inout int z);begin #1;q=x;z+=x;end endtask
shortint output_value;
initial begin
$display("TRACE defaults %h %h %h",result,small_value,large_value);
small_value=f(8'b1xz001zx);result=h(32'hx0000009);large_value=k(64'hxz000000ffffffff);wide=mask(80'hxz123456789abcdef012);
$display("TRACE calls %h %h %h %h %h %h",small_value,g(16'hffff),result,large_value,wide,one(1'bz));
result=10;update(8'b1xz001zx,output_value,result);
$display("TRACE task %0d %0d",output_value,result);
four=mask(80'hx);$display("TRACE return %h",four);#1;$finish;
end
endmodule
