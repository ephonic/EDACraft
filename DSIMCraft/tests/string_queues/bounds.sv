module top;
 string q[$:1],s;int calls,observed;
 function automatic string item();calls++;return $sformatf("item%0d",calls);endfunction
 initial begin
  q.push_back(item());q.push_back(item());q.push_back(item());
  if(calls!=3||q.size()!=2||q[0]!="item1"||q[1]!="item2")$fatal(1,"full back");
  q.push_front("front");if(q[0]!="front"||q[1]!="item1")$fatal(1,"full front");
  q.insert(1,"insert");
  if(q.size()!=2||q[1]!="insert")$fatal(1,"bound insert");
  s=q.pop_front();q.delete(0);q.delete();
  if(q.pop_back()!=""||q[0]!="")$fatal(1,"defaults");
  observed=calls;$display("TRACE bounds %s %0d",s,observed);$finish;
 end
endmodule
