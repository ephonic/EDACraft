package Maps;int data[int][string];endpackage
module bank;int data[int][string];endmodule
module top;
 typedef logic[3:0] elem_t;elem_t source[int][string];bit[3:0] dest[int][string];
 int observed;bank u();
 function automatic int recursive(int n);
  int local_map[int][string];int subtotal;
  local_map[1]["v"]=n;
  if(n>0)subtotal=recursive(n-1);
  return local_map[1]["v"]+subtotal;
 endfunction
 initial begin
  source[3]["x"]=4'bx1z1;dest=source;
  if(dest[3]["x"]!==4'b0101||source[3]["x"]!==4'bx1z1)$fatal(1,"nested state copy");
  Maps::data[-1]["pkg"]=7;
  u.data[2]["hier"]=9;
  if(u.data[2].num()!=1||!u.data.exists(2))$fatal(1,"hierarchical methods");
  observed=recursive(4)+Maps::data[-1]["pkg"]+u.data[2]["hier"];
  $display("TRACE storage %0d %0d",observed,dest[3]["x"]);
 end
endmodule
