`timescale 1ns/1ps
module top;
typedef enum logic[3:0] {A=2,B=7,C=1} E;
integer calls=0,steps=0;
E e,answer;
function automatic E get(input E value);calls++;return value;endfunction
function automatic int step();steps++;return 2;endfunction
function automatic E advance(input E value,input int n);
 E local_value;local_value=value.next(n);return local_value.prev();
endfunction
task automatic later(input E value,output E result);
 E local_value;local_value=value.next();#2;result=local_value.prev(2);
endtask
initial begin
e=A;answer=get(e).next(step());
if(answer!==C||calls!==1||steps!==1)$fatal(1,"once");
answer=get(B).first();if(answer!==A||calls!==2)$fatal(1,"first receiver once");
answer=advance(e,2);if(answer!==B)$fatal(1,"function identity");
e<=#2 e.next();later(C,answer);
#1;
if(answer!==B||e!==B)$fatal(1,"delay capture");
#1;answer=get(e).last();
if(answer!==C||calls!==3)$fatal(1,"last receiver once");
if(get(e).num()!==3||calls!==3)$fatal(1,"num is metadata only");
$display("TRACE effects %0d %0d %0d %0d",e,answer,calls,steps);
end
endmodule
