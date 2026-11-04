module top;
 typedef int Q[$];Q a[string][int],copy[string][int];int observed,visits;string keys[$];
 initial begin
  a["b"][4].push_back(8);a["a"][-1]='{2,3};a["b"][2]='{5};copy=a;
  a["a"][-1][0]=20;a["b"].delete(4);
  foreach(copy[name,key,index])begin observed+=copy[name][key][index];visits++;end
  if(observed!=18||visits!=4||copy["a"][-1][0]!=2||copy["b"].num()!=2||a["b"].num()!=1)$fatal(1,"nested deep copy");
  foreach(copy[name,key])copy[name][key].push_front(1);
  if(copy["b"][4].size()!=2||copy["a"][-1].size()!=3)$fatal(1,"prefix foreach");
  copy.delete("a");if(copy.num()!=1||copy["b"].num()!=2)$fatal(1,"branch delete");
  $display("TRACE mixed nested %0d %0d",observed,visits);$finish;
 end
endmodule
