`timescale 1ns/1ps
module top;
 integer n=3,calls=0;
 integer a[]=new[n];
 function automatic integer prepare();
  calls++;a[0]=17;return n+2;
 endfunction
 integer b[]=new[prepare()](a),c[]=a,empty[]=new[0];
 integer fixed_src[2];integer f[]=new[3](fixed_src);
 integer observed=0;
 task work;
  integer local_values[]=new[n];
  $display("TRACE local %0d %0d %h",local_values.size(),n,local_values[0]);
  local_values[0]=7;
 endtask
 initial begin
  $display("TRACE static %0d %0d %0d %0d %0d %0d %h %h",a.size(),b.size(),c.size(),f.size(),empty.size(),calls,b[0],b[4]);
  a[0]=9;n=5;work();work();
  observed=b[0]+c[0];
  $display("TRACE copied %0d %0d %0d",a[0],b[0],c[0]);
  #1;b[0]=31;observed=b[0]+c[0];
 end
endmodule
