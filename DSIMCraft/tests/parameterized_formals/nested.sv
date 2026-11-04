module top;
 class Node#(type T=int);T value;function new(T n);value=n;endfunction endclass
 function logic[70:0] sum(int prefix,Node#(Node#(logic[(3+5)*9-2:0])) leaf);
  return prefix+leaf.value.value;
 endfunction
 Node#(logic[70:0]) a;Node#(Node#(logic[70:0])) b;
 logic[70:0] observed;
 initial begin
  a=new(71'h400000000000000001);b=new(a);observed=sum(2,b);
  $display("TRACE nested %h",observed);
 end
endmodule
