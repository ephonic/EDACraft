`timescale 1ps/1ps
module top;
 class C;
  event pulse;int value;
  function new(int n);value=n;endfunction
  task sample(output int result);@(pulse);#1;result=value;endtask
  task fire();->pulse;endtask
 endclass
 C a,b;int x=0,y=0,done=0;
 task automatic round();
  fork
   begin a.sample(x);done++;end
   begin b.sample(y);done++;end
   begin #1;a.fire();#1;b.fire();end
  join
 endtask
 initial begin
  a=new(11);b=new(29);round();
  if(x!=11||y!=29||done!=2)$fatal(1,"concurrent method frames");
  a.value=17;b.value=31;round();
  if(x!=17||y!=31||done!=4)$fatal(1,"method frame reuse");
  $display("TRACE class tasks %0d %0d %0d",x,y,done);$finish;
 end
 initial begin #100;$fatal(1,"method wait lost");end
endmodule
