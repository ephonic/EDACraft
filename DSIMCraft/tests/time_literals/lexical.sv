package timing;
 timeunit 10ns/1ps;
 parameter realtime P=250ps;
 class timer #(parameter int N=2);
  const realtime amount=2.5ns;
  function realtime value(input realtime extra=500ps);return amount+extra+N*1ns;endfunction
 endclass
 function automatic realtime value(input realtime d=250ps);return P+d;endfunction
endpackage
module child #(parameter realtime D=250ps)(output int observed);
 timeunit 1ns/100ps;
 initial begin observed=0;#D;observed=1;end
endmodule
module top;
 timeunit 100ps/10ps;
 timing::timer #(2) a;timing::timer #(4) b;
 int x,y;child one(x);child #(.D(350ps)) two(y);
 initial begin
  a=new();b=new();
  if(timing::P!=0.025||timing::value()!=0.05||a.value()!=0.5||b.value()!=0.7)$fatal(1,"lexical scope");
  #10ns;
  if(x!=1||y!=1)$fatal(1,"parameter delays");
  $display("TRACE lexical %0.17g %0.17g %0.17g %0.17g",timing::P,timing::value(),a.value(),b.value());
  $finish;
 end
endmodule
