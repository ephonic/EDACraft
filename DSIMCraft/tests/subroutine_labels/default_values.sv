module top;
 int a=100,b=200,calls=0,observed;
 function automatic int next_value();calls++;return calls+6;endfunction : next_value
 function automatic int add(int x,int y=x+1);return y;endfunction : add
 function automatic int chain(int a,b=a+1,c=add(b));return c;endfunction : chain
 function automatic int future(int a=b+1,int b=2);return a;endfunction : future
 function automatic int self(int a=a+1);return a;endfunction : self
 function automatic int local_shadow(int x=a);int a=9;return x;endfunction : local_shadow
 function automatic int narrow(bit[3:0] a,int b=a+1);return b;endfunction : narrow
 function automatic int state2(bit[3:0] a,int b=a+1);return b;endfunction : state2
 function automatic int recur(int n,int v=n+2);
  if(n==0)return v;return v+recur(n-1);
 endfunction : recur
 initial begin
  observed=chain(next_value());
  if(observed!=9||calls!=1)$fatal(1,"default repeated an actual");
  $display("TRACE defaults chain %0d %0d %0d %0d",observed,calls,chain(.a(19)),chain(2,,30));
  $display("TRACE defaults scope %0d %0d %0d %0d",future(),future(.b(7)),self(),local_shadow());
  $display("TRACE defaults converted %0d %0d %0d",narrow(31),state2(4'bx1z1),recur(3));
  #1;observed=chain(.a(10),.c());
  if(observed!=12||calls!=1)$fatal(1,"named default");
  $display("TRACE defaults named %0d",observed);#1;$finish;
 end
endmodule
