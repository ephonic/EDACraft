`timescale 1ns/1ps
module top;
integer total=0,a=0,b=0,ca=0,cb=0;
function integer add(input integer x,output integer copy);
 begin total+=x;copy=total;return total;end
endfunction
function void noop();begin return;end endfunction
task nop();begin end endtask
initial begin nop();noop();void'(noop());#1 a=add(3,ca);#4 a=add(5,ca);end
initial begin #2 b=add(7,cb);#4 b=add(11,cb);end
initial begin
 #7 if(total!==26||a!==15||b!==26||ca!==15||cb!==26)$fatal(1,"shared function writes");
 $display("TRACE shared complete");
end
endmodule
