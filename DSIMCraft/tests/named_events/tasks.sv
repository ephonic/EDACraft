`timescale 1ns/1ps
module worker #(parameter BASE=3)(output integer result);
 event ready_event;
 function automatic void fire();->ready_event;endfunction
 task automatic await_value(input integer seed,output integer out);
   integer saved;begin saved=seed;@ready_event;#1;out=saved+BASE;end
 endtask
 initial begin result=0;await_value(7,result);await_value(11,result);end
 initial begin #1;fire();#2;->> ready_event;end
endmodule
module top;
 integer left,right,local_result;logic signal_flag;
 worker #(3)u(left);worker #(9)v(right);
 initial begin:local_block
   event local_event;integer count;
   count=0;signal_flag=0;->> #1 local_event;@(local_event or signal_flag);count++;
   #1;signal_flag=1;@(local_event or negedge signal_flag);count++;local_result=count;
 end
 initial begin #3;signal_flag=0;end
 initial begin #5;
   if(left!==14||right!==20||local_result!==2)$fatal(1,"event tasks and scopes");
   $display("TRACE tasks %0d %0d %0d",left,right,local_result);$finish;
 end
endmodule
