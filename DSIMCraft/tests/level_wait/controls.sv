`timescale 1ns/1ps
module worker #(parameter BASE=3)(input logic gate,output integer result);
 task automatic await_value(input integer seed,output integer out);
   integer saved;
   begin saved=seed;wait(gate) #1 out=saved+BASE;end
 endtask
 initial begin result=0;await_value(7,result);wait(!gate);await_value(11,result);end
endmodule
module top;
 logic gate;integer left,right,selected,k,pulse_done;logic pulse;
 worker #(3)u(gate,left);worker #(9)v(gate,right);
 initial begin selected=0;wait(gate)if(0)selected=1;else selected=2;end
 initial begin k=0;while(k<3)begin k=k+1;wait(gate);if(k==1)continue;if(k==2)break;end end
 initial begin pulse=0;pulse_done=0;wait(pulse);pulse_done=1;end
 initial begin gate=0;#1;pulse=1;pulse=0;#1;gate=1;
   #2;if(left!==10||right!==16||selected!==2||k!==2||pulse_done!==0)$fatal(1,"wait controls");
   gate=0;#1;gate=1;#2;
   if(left!==14||right!==20)$fatal(1,"task reentry");
   $display("TRACE controls %0d %0d %0d %0d %0d",left,right,selected,k,pulse_done);$finish;
 end
endmodule
