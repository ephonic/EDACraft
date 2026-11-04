`timescale 1ns/1ps
module top;
time answer=0;
reg signed[63:0] negative=0;
integer unsigned quotient=0;
integer source=-1;
function integer unsigned div3(input integer unsigned value);
 begin return value/3;end
endfunction
function time nextstamp(input time value);
 begin return value+64'h100000000;end
endfunction
function signed[63:0] divtime(input signed[63:0] value);
 begin return value/3;end
endfunction
task update(input time value,output time result,inout integer unsigned accum);
 time local_stamp;
 begin local_stamp=value;#1;result=nextstamp(local_stamp++);accum+=div3(accum);return;end
endtask
initial begin
 quotient=32'hffffffff;
 #1;negative=divtime(-64'sd17);update(64'habcdef0100000000,answer,quotient);
 $display("TRACE calls %h %0d %0d",answer,negative,quotient);
 answer=nextstamp(64'hffffffffffffffff);source=div3(32'hffffffff);
 $display("TRACE returns %h %0d",answer,source);
 #1;$finish;
end
endmodule
