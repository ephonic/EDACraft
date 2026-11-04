`timescale 1ns/1ps
module worker(output logic[15:0] q=0);
 bit[7:0] zeros[2];logic[7:0] seeded[2]=zeros;integer calls=0;
 function automatic integer seed();seeded[0]=8'h84;seeded[1]=2;calls++;return 0;endfunction
 integer trigger[]=new[seed()];bit[7:0] copy[2]=seeded;
 task automatic work(input integer n);
  logic[7:0] local_values[2]=copy;
  local_values[0]+=n;#1;q={local_values[0],local_values[1]};
 endtask
 initial begin work(1);#1;work(2);end
endmodule
module top;wire[15:0] one,two;worker a(one);worker b(two);endmodule
