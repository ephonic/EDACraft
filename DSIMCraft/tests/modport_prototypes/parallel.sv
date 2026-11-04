`timescale 1ns/1ps
interface lane_bus #(parameter BASE=3);
 integer value=0;
 task automatic next(input integer i);#1;value=BASE+i*3;endtask
 function automatic integer read();return value;endfunction
 modport user_api(import task next(input integer i), function integer read(),input value);
endinterface
module worker #(parameter PERIOD=5,COUNT=6,BASE=3)(lane_bus.user_api p,output integer q=0,output integer errors=0);
 integer i;
 initial begin for(i=0;i<COUNT;i++)begin #(PERIOD);p.next(i);q=p.read();if(q!=BASE+i*3)errors++;end end
endmodule
module lane #(parameter PERIOD=5,COUNT=6,BASE=3)(output wire[31:0] q,output wire[31:0] errors);
 lane_bus #(BASE) b();worker #(PERIOD,COUNT,BASE) u(b,q,errors);
endmodule
module top;
 wire[31:0] one,two,error_one,error_two;
 lane #(5,6,3) a(one,error_one);lane #(7,4,17) b(two,error_two);
endmodule
