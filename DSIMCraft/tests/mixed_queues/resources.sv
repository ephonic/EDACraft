module top;
 class Resource;
  int precedence;
  function new(int p);precedence=p;endfunction
 endclass
 typedef Resource queue_t[$];
 queue_t all[int];Resource a,b;int observed;
 initial begin
  a=new(10);b=new(5);all[2].push_front(a);all[2].push_front(b);
  if(all.num()!=1||all[2].size()!=2||all[2][0].precedence!=5)$fatal(1,"associative queue");
  foreach(all[key,index])observed+=all[key][index].precedence;
  if(observed!=15)$fatal(1,"mixed foreach");
  $display("TRACE associative_queue %0d",observed);$finish;
 end
endmodule
