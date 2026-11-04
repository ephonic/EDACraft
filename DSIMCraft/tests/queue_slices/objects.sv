class Box;
  string values[$];
  function new(); values='{"A","B","C","D"}; endfunction
  function void trim(input int count); values=values[0:count-1]; endfunction
endclass
module top;
  Box a,b;
  int stage=0;
  initial begin
    a=new(); b=new();
    a.trim(2); stage++; #1;
    $display("TRACE trim %0d %s %s other=%0d",a.values.size(),a.values[0],a.values[1],b.values.size());
    b.values=a.values[1:$]; stage++; #1;
    $display("TRACE copy %0d %s source=%0d",b.values.size(),b.values[0],a.values.size());
    a.trim(0); stage++; #1;
    $display("TRACE clear %0d other=%0d",a.values.size(),b.values.size());
    b.trim(20); stage++; #1;
    $display("TRACE clip %0d %s",b.values.size(),b.values[0]);
    $finish;
  end
endmodule
