`timescale 1ns/1ps
module top;
 int q[$], b[$:2], copy[$], da[], total=0, count=0, index=0;
 function automatic int value(input int v);count++;return v;endfunction
 initial begin
   q.push_back(value(11));q.push_front(value(-2));q.insert(value(1),value(7));
   $display("TRACE queue %0d %0d %0d %0d %0d",q.size(),q[0],q[1],q[2],count);
   copy=q;da=q;q.delete(1);q[q.size()]=value(9);q[-1]=99;q[99]=99;
   #2;
   $display("TRACE copy %0d %0d %0d %0d %0d",q.size(),copy.size(),da.size(),copy[1],q[2]);
   foreach(q[i]) total+=q[i];
   $display("TRACE foreach %0d %0d %0d",total,q.sum(),q.product());
   q.delete();q=da;q[index++]+=value(3);
   $display("TRACE update %0d %0d %0d %0d",q[0],index,count,q.pop_front());
   b.push_back(1);b.push_back(2);b.push_back(3);b.push_back(4);b.push_front(9);b.insert(1,8);
   $display("TRACE bound %0d %0d %0d %0d",b.size(),b[0],b[1],b[2]);
   b=copy;
   $display("TRACE assign %0d %0d %0d %0d",b.size(),b[0],b[1],b[2]);
   #2;q.delete();b.delete();copy.delete();da.delete();
   $display("TRACE clear %0d %0d %0d %0d",q.size(),b.size(),copy.size(),da.size());
 end
endmodule
