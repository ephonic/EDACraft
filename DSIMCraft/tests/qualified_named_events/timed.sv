`timescale 1ns/1ps
module top;event e;logic enabled=0;integer seen=0,late=0,persistent=0;
function automatic logic allow();return enabled;endfunction
always @(e iff allow())seen++;
initial begin #1;#0;@(e iff allow());late++;end
initial begin #1;#0;wait(e.triggered);persistent=1;end
initial begin
->>#2 e;
#1 enabled=1;->e;
#1 enabled=0;#0;enabled=1;
#1 ->>#2 e;
#1 enabled=0;
#1;#0;enabled=1;
#1 ->>e;
#1 $display("TRACE timed %0d %0d %0d",seen,late,persistent);
if(seen!==4||late!==1||persistent!==1)$fatal(1,"timed mismatch");$finish;end
endmodule
