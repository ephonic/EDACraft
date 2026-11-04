`timescale 1ps/1ps
package types;
 class Item;
  string name="item";
  int value=5;
  logic [7:0] flags=8'b10xz0011;
  function new(string label="new",int value=7);name=label;this.value=value;endfunction
  function string describe();return $sformatf("%s:%0d",name,value);endfunction
 endclass
 typedef Item Alias;
 function automatic int get(Item p);return p.value;endfunction
endpackage
module top;
 import types::*;
 Item a;Alias b;int observed;logic [7:0] observed_flags;
 initial begin
  a=new("hello",31);b=a;
  observed=get(a);observed_flags=b.flags;
  $display("TRACE package=%s value=%0d flags=%b",b.describe(),get(a),b.flags);
  b.name="updated";
  $display("TRACE text=%s len=%0d",a.name,a.name.len());
  $finish;
 end
endmodule
