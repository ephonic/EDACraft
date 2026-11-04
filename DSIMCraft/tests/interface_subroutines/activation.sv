`timescale 1ns/1ps
interface shared_bus;
 integer value=0;
 task automatic transact(input integer n,input integer wait_ns,ref integer live,output integer snapshot);
  integer saved;
  saved=n;#(wait_ns);value+=saved;live+=saved;snapshot=value;#1;
 endtask
 modport api(import transact,input value);
endinterface
module client(shared_bus.api p);
 integer live=1,one,two;
 initial begin
  fork
   p.transact(3,4,live,one);
   p.transact(5,2,live,two);
  join
  if(live!=9||one!=8||two!=5||p.value!=8)$fatal(1,"FAIL overlapping automatic task frames");
  $display("TRACE activation %0d %0d %0d %0d",live,one,two,p.value);
 end
endmodule
module top;shared_bus b();client c(b);initial begin #8;$finish;end endmodule
