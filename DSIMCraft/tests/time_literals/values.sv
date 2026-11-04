module top;
 timeunit 1ns/100ps;
 realtime a=1.25ns,b=1.24ns,c=250ps,d=0.05ns,e=9200s;
 time t=1.5ns;
 int observed=0;
 initial begin
  if(a!=1.25||b!=1.24||c!=0.25||d!=0.05||e!=9.2e12||t!=2)$fatal(1,"literal value");
  $display("TRACE values %0.17g %0.17g %0.17g %0d",a,b,c,t);
  #1.25ns;observed=1;
  $display("TRACE tick %0.17g %0d",$realtime,$time);
  #250ps;observed=2;
  $display("TRACE end %0.17g",$realtime);$finish;
 end
endmodule
