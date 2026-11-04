module store #(parameter W=8)(output int result);
 class Cell;
  logic[W-1:0] values[int];
 endclass
 Cell nodes[2];
 function automatic int total();
  int sum=0;
  foreach(nodes[1].values[key])sum+=nodes[1].values[key];
  return sum;
 endfunction
 initial begin
  nodes[0]=new;nodes[1]=new;
  nodes[1].values[1]='1;nodes[1].values[3]=2;
  result=total();
 end
endmodule
module top;
 int a,b;
 store #(4) narrow_h(a);
 store #(9) wide_h(b);
 initial begin
  #1;if(a!=17 || b!=513)$fatal(1,"foreach specialization and local binding");
  $display("TRACE foreach clones results=%0d,%0d",a,b);$finish;
 end
endmodule
