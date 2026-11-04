module top;
 typedef int Q[$];Q a,b;int calls=0;logic equal;
 function automatic Q get_a();calls++;return a;endfunction
 function automatic Q get_b();calls++;a.push_back(99);return b;endfunction
 function automatic bit compare(ref Q x,ref Q y);return x===y;endfunction
 always @(a==b) equal=(a==b);
 initial begin
  #1;a.push_back(5);b.push_back(5);#1;
  $display("TRACE observe %b",equal);
  $display("TRACE snapshot %b",get_a()===get_b());
  $display("TRACE effects %0d %0d %0d",calls,a.size(),b.size());#1;
  $display("TRACE ref %b %b",compare(a,b),equal);
  b.push_back(99);#1;$display("TRACE changed %b %b",compare(a,b),equal);
 end
endmodule
