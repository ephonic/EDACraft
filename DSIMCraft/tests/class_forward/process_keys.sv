`timescale 1ps/1ps
module top;
 // The first mention of process is an index type, including in a template.
 class Tracker#(type T=int);
  T values[process];
  function void put(process p,T x);values[p]=x;endfunction
  function T get(process p);return values[p];endfunction
 endclass
 int data[process];process current,cursor;Tracker#(int) tracker;int observed,count;
 initial begin
  current=process::self();tracker=new;data[current]=11;tracker.put(current,19);
  foreach(data[p])begin if(p==current)count++;end
  if(!data.first(cursor)||cursor!=current)$fatal(1,"process cursor");
  observed=data[cursor]+tracker.get(current);#1;
  $display("TRACE process keys %0d %0d %0d",observed,count,tracker.values.exists(current));
 end
endmodule
