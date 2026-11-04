`timescale 1ps/1ps
module top;
 function automatic int local_init(int n);
  int previous=n==0?1:local_init(n-1);
  return previous+n;
 endfunction
 function automatic int a(int n);
  int saved=n;
  if(n==0)return 1;
  return b(n-1)+saved;
 endfunction
 function automatic int b(int n);
  int saved=n;
  if(n==0)return 2;
  return c(n-1)+saved;
 endfunction
 function automatic int c(int n);
  int saved=n;
  if(n==0)return 3;
  return a(n-1)+saved;
 endfunction
 function automatic int aa(int n);
  if(n==0)return 1;
  return bb(n-1)+n;
 endfunction
 function int bb(int n);
  begin: block_init
   automatic int local_value=n==0?2:aa(n-1);
   return local_value+n;
  end
 endfunction
 int observed;
 initial begin
  observed=a(6);
  if(observed!=22||b(6)!=23||c(6)!=24||local_init(4)!=11||aa(4)!=9||bb(4)!=6)$fatal(1,"recursive activation initializers");
  #2 $display("TRACE recursive initializers cycle pass");$finish;
 end
endmodule
