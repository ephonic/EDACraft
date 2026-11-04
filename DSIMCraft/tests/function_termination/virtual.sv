module top;
 class base;virtual function void die();$display("BAD base");endfunction endclass
 class child extends base;virtual function void die();$display("TRACE die");$finish; $display("BAD method");endfunction endclass
 base item;child derived;
 initial begin derived=new();item=derived;#1;item.die();$display("BAD caller");end
 final $display("TRACE final");
 endmodule
