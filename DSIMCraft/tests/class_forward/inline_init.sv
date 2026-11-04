`timescale 1ps/1ps
module lane #(parameter W=65)(output logic [W-1:0] observed);
 typedef class Reporter;
 class Client;
 static function logic [W-1:0] invoke();
  Reporter r;
  r=new;
  return r.value();
 endfunction
  static function logic [W-1:0] read();
   logic [W-1:0] n=invoke();
   return n;
  endfunction
  static task read_task(output logic [W-1:0] out);
   logic [W-1:0] n=invoke();
   #1;out=n;
  endtask
 endclass
 typedef class Handler;
 class Reporter;
  Handler h;
  function logic [W-1:0] value();h=new;return h.bits;endfunction
 endclass
 class Handler;logic [W-1:0] bits='1;endclass
 initial begin
  observed=Client::read();
  if(observed!=='1)$fatal(1,"function initializer");
  observed=0;
  Client::read_task(observed);
  if(observed!=='1)$fatal(1,"task initializer");
 end
endmodule
module top;
 wire [64:0] a;wire [128:0] b;
 lane #(65) one(a);lane #(129) two(b);
 initial begin #2;$display("TRACE inline %h %h",a,b);end
endmodule
