`timescale 1ns/1ps
package shared;
 integer count=3;
 int values[0:1]='{4,5};
 typedef enum logic[1:0]{IDLE,RUN,DONE} phase_t;
 phase_t phase=IDLE;
 string label="seed";
 function automatic integer bump(input integer delta);
  count=count+delta;return count;
 endfunction
 task automatic later(input integer delta);
  #1;count<=count+delta;values[1]<=count;
 endtask
endpackage
module writer(output integer seen);
 import shared::count;
 initial begin #1;count=count+2;seen=count;#2;shared::later(4);end
endmodule
module reader(output integer seen);
 import shared::*;
 initial begin #2;seen=bump(3);phase=RUN;values[0]=count;label={label,"!"};end
endmodule
module top;
 import shared::*;
 wire[31:0] a,b;writer u(a);reader v(b);
 integer count=99,answer=0;
 initial begin
  #0.5;if(shared::count!==3||count!==99)$fatal(1,"FAIL init/shadow");
  #2;if(shared::count!==8||a!==5||b!==8||values[0]!==8||phase.name!="RUN"||label!="seed!")$fatal(1,"FAIL shared");
  $display("TRACE package shared %0d %0d %0d %s %s",shared::count,a,b,phase.name,label);
  #2;if(shared::count!==12||values[1]!==8)$fatal(1,"FAIL task NBA");
  answer=shared::bump(1);shared::values[0]=answer;
  if(answer!==13||shared::count!==13||values[0]!==13)$fatal(1,"FAIL qualified writes");
  $display("TRACE package final %0d %0d",shared::count,values[0]);#0.5;$finish;
 end
endmodule
