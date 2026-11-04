module top;
 class Leaf;int values[string];endclass
 class Branch;Leaf child;endclass
 Branch branches[2];
 int observed;
 initial begin
  branches[0]=new;branches[0].child=new;
  branches[1]=new;branches[1].child=new;
  branches[0].child.values["x"]=3;branches[0].child.values["y"]=8;
  observed=0;
  foreach(branches[s])
   foreach(branches[s].child.values[k])observed+=branches[s].child.values[k];
  if(observed!=11)$fatal(1,"deep receiver");
  $display("TRACE foreach deep observed=%0d",observed);$finish;
 end
endmodule
