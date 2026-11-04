module top;
 class Store;int data[int][int];endclass
 Store a;int calls,observed,indices[$];
 function Store get_store();calls++;return a;endfunction
 initial begin
  a=new;a.data[1][2]=7;a.data[1][3]=8;
  indices=get_store().data[1].find_index() with(item>7);
  if(calls!=1||indices.size()!=1||indices[0]!=3)$fatal(1,"receiver evaluated twice");
  observed=get_store().data[1][2]++;
  if(calls!=2||observed!=7||a.data[1][2]!=8)$fatal(1,"postfix receiver capture");
  $display("TRACE receiver %0d %0d",calls,observed);
 end
endmodule
