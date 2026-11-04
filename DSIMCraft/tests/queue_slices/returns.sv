typedef int values_t[$];
module top;
  values_t q,r;
  int stage=0;
  function automatic values_t middle(input values_t source,input int first,input int last);
    return source[first:last];
  endfunction
  initial begin
    q='{10,20,30,40,50}; r=middle(q,1,3); stage++; #1;
    $display("TRACE return %0d %0d/%0d/%0d",r.size(),r[0],r[1],r[2]);
    r[0]=99; stage++; #1;
    $display("TRACE independent %0d/%0d",q[1],r[0]);
    r=middle(q,3,1); stage++; #1;
    $display("TRACE empty return %0d",r.size()); $finish;
  end
endmodule
