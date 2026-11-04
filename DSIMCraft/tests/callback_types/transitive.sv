class Base #(type T=int);T value;endclass
class Middle #(type T=int) extends Base#(T);endclass
class Leaf #(type T=int) extends Middle#(T);
 function new(T value);this.value=value;endfunction
endclass
module top;
 Leaf#(bit[64:0]) leaf;Base#(bit[64:0]) base;Middle#(bit[64:0]) middle;
 bit[64:0] observed;int stage=0;
 function automatic Base#(bit[64:0]) up(input Leaf#(bit[64:0]) value);return value;endfunction
 initial begin
  leaf=new(65'h10000000000000003);base=up(leaf);middle=leaf;
  observed=base.value;$display("TRACE transitive %h %0d",observed,base==middle);stage++;#1;
  middle.value=65'h10000000000000007;observed=base.value;$display("TRACE alias %h",observed);$finish;
 end
endmodule
