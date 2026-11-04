`timescale 1ns/1ps
module worker #(parameter INDEX=3)(output integer result);
 event kick;logic[7:0]bus;logic enable;
 task automatic watch(input integer index,output integer value);
 integer saved;
 begin saved=0;@(bus[index] or kick);saved++;@(posedge (bus[index]^enable));saved+=2;value=saved;end
 endtask
 integer first,second;
 initial begin result=0;#0;watch(INDEX,first);watch(INDEX,second);result=first+second;end
 initial begin bus=0;enable=0;#1;->>kick;#1;bus[INDEX]=1;#1;->>kick;#1;enable=1;#1;bus[INDEX]=0;end
endmodule
module top;
 integer a,b;worker #(3)u(a);worker #(1)v(b);
 initial begin #7;if(a!==6||b!==6)$fatal(1,"event expressions in automatic tasks");
 $display("TRACE tasks %0d %0d",a,b);$finish;end
endmodule
