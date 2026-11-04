`timescale 1ps/1ps
package items;
 typedef class Handle;
 class Client;
  extern function Handle pass(Handle value);
 endclass
 class Item;int value=37;endclass
 typedef Item Handle;
 function Handle Client::pass(Handle value);return value;endfunction
endpackage
module top;import items::*;
 class Local;typedef class Handle;class Item;int value=41;endclass typedef Item Handle;Handle item=new;endclass
 Handle item=new;Client c;Local local_item;int observed;
 initial begin c=new;local_item=new;observed=c.pass(item).value+local_item.item.value;
 #1;$display("TRACE package alias %0d",observed);end
endmodule
