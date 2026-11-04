`timescale 1ns/1ps
class Item;
 int value;
 function new(int n=0);value=n;endfunction
endclass
class Factory;
 function automatic int walk(int n, ref Item history[$], ref int count);
  Item item;
  item=new(n);history.push_back(item);count++;
  if(n==0)return history.size();
  return step(n-1,history,count)+n;
 endfunction
 function automatic int step(int n, ref Item history[$], ref int count);
  return walk(n,history,count);
 endfunction
endclass
module top;
 Factory f;
 Item history[$];
 int count,result;
 int source[3]='{3,5,7};
 int dynamic_source[];
 function automatic int sum(int n, const ref int data[3]);
  if(n==0)return data[0];
  return data[n]+sum(n-1,data);
 endfunction
 function automatic int copied(int n,input int data[]);
  if(n==0)return data[0];
  data[n]+=1;
  return data[n]+copied(n-1,data);
 endfunction
 initial begin
  f=new;count=0;result=f.walk(4,history,count);
  $display("TRACE queue %0d %0d %0d %0d %0d",result,count,history.size(),history[0].value,history[4].value);
  dynamic_source=new[3];dynamic_source[0]=3;dynamic_source[1]=5;dynamic_source[2]=7;
  $display("TRACE arrays %0d %0d %0d",sum(2,source),copied(2,dynamic_source),dynamic_source[2]);
  #1;result=f.walk(1,history,count);
  $display("TRACE second %0d %0d %0d",result,count,history.size());
 end
endmodule
