module top;
 typedef int Q[$];
 typedef Q Qalias;
 typedef int D[];
 typedef int F[3:1];
 Q q,saved;D d;F f;
 int calls;
 function automatic Q make(input int n);
  Qalias temp;
  calls++;
  for(int i=0;i<n;i++)temp.push_back(i+10);
  return temp;
 endfunction : make
 function automatic Q relay(input int n);
  return make(n);
 endfunction : relay
 function automatic F fixed_make(input int n);
  F temp;foreach(temp[i])temp[i]=n+i;
  return temp;
 endfunction : fixed_make
 function automatic int total(input Q values);
  int result;result=0;foreach(values[i])result+=values[i];return result;
 endfunction : total
 initial begin
  q=relay(3);saved=q;q[0]=5;
  $display("TRACE queue %0d %0d %0d %0d",q.size(),saved[0],total(make(2)),calls);
  d=make(4);f=fixed_make(20);
  $display("TRACE array %0d %0d %0d %0d",d.size(),d[3],f[3],f[1]);
  $display("TRACE temporary %0d",make(2).size());
  #1;q=make(1);$display("TRACE frame %0d %0d",q.size(),saved.size());#1;$finish;
 end
endmodule
