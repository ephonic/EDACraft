`timescale 1ns/1ps
module top;
typedef enum logic[3:0] {A=2,B=7,C=1,X=4'bx101,Z=4'bz010} E;
typedef enum bit[2:0] {U=3,V=5,W=7} Two;
E e,next_value,prev_value;Two t;
logic[31:0] amount;
initial begin
e=E'(9);t=Two'(1);
if(e.next()!==4'bxxxx||e.prev(0)!==4'bxxxx||t.next()!==0||t.prev(0)!==0)$fatal(1,"invalid");
e=X;next_value=e.next();prev_value=e.prev();
if(next_value!==Z||prev_value!==C||e.next(0)!==X)$fatal(1,"four state member");
#1;e=Z;if(e.next()!==A||e.prev()!==X)$fatal(1,"four state wrap");
e=A;amount=32'b0x1;next_value=e.next(amount);prev_value=e.prev(amount);
if(next_value!==X||prev_value!==C)$fatal(1,"partially unknown count aval compatibility");
amount='x;if(e.next(amount)!==A)$fatal(1,"unknown count");
amount='z;if(e.prev(amount)!==A)$fatal(1,"high impedance count");
e=E'(4'bx100);if(e.next()!==4'bxxxx)$fatal(1,"invalid unknown current");
$display("TRACE edges %b %b %b %0d",e,next_value,prev_value,t);
end
endmodule
