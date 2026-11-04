`timescale 1ps/1ps
module top;
 class Key;int id;function new(int n);id=n;endfunction endclass
 class Store;
  int values[Key];
  function int total();int sum;foreach(values[k])if(k!=null)sum+=k.id+values[k];return sum;endfunction
  function void put(Key k,int n);values[k]=n;endfunction
 endclass
 Store one,two;Key a,b,key,selected[$];int observed;
 initial begin
  one=new;two=new;a=new(3);b=new(7);
  one.put(a,10);one.put(b,20);two.values=one.values;
  one.values[a][3:0]=5;
  if(one.values[a]!=5||two.values[a]!=10)$fatal(1,"field copy and slice");
  selected=one.values.find_index with(item>=15);
  if(selected.size()!=1||selected[0]!=b)$fatal(1,"typed locator");
  foreach(one.values[k])if(k.id==7)one.values[k]+=2;
  observed=one.total();
  if(observed!=37||two.total()!=40)$fatal(1,"typed class foreach");
  if(!one.values.last(key)||key==null)$fatal(1,"field cursor");
  #2;one.values.delete();
  if(one.values.num()!=0||two.values.num()!=2)$fatal(1,"independent containers");
  $display("TRACE fields %0d %0d",observed,two.total());$finish;
 end
endmodule
