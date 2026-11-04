module top;
 class Key;int id;function new(int i);id=i;endfunction endclass
 typedef int Q[$:1];Q a[Key],copy[Key];Key one,two;int observed;
 initial begin
  one=new(1);two=new(2);a[one].push_back(4);a[one].push_back(5);a[one].push_back(6);a[two]='{7};copy=a;
  a.delete(one);if(a.num()!=1||copy[one].size()!=2||copy[one][1]!=5)$fatal(1,"class keys ownership");
  foreach(copy[key,i])observed+=key.id+copy[key][i];
  if(observed!=20)$fatal(1,"class foreach");$display("TRACE mixed class_keys %0d",observed);$finish;
 end
endmodule
