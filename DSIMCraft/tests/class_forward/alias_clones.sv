`timescale 1ps/1ps
module leaf #(parameter W=8);
 typedef class Handle;typedef Handle Alias;
 class Client;Alias item;function Handle pass(Handle x);return x;endfunction endclass
 class Store #(type T=int);T value='1;endclass
 typedef Store#(logic[W-1:0]) Handle;
 Alias item=new;Client c;logic[W-1:0] observed;
 initial begin c=new;c.item=item;observed=c.pass(item).value;#1;$display("TRACE clone %0d %h",W,observed);end
endmodule
module top;leaf#(65) one();leaf#(129) two();endmodule
