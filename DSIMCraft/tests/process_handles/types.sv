package pkg;
 typedef process proc_t;
 function automatic proc_t current();return proc_t::self();endfunction
 function automatic int self();return 13;endfunction
endpackage
module leaf #(parameter N=1);
 process p;pkg::proc_t alias_handle;
 initial begin p=process::self();alias_handle=pkg::current();if(p!=alias_handle)$fatal(1,"canonical type");end
endmodule
module top;
 process p,q;process::state st;
 class Holder;process p;function new(process arg);p=arg;endfunction endclass
 Holder box;
 leaf #(2) one();leaf #(3) two();
 function automatic process accept(process arg);return arg;endfunction
 initial begin
  p=pkg::current();q=accept(p);box=new(q);st=process::RUNNING;
  if(p!=box.p||process::FINISHED!=0||st!=1||process::WAITING!=2||process::SUSPENDED!=3||process::KILLED!=4)$fatal(1,"process types");
  if(pkg::self()!=13)$fatal(1,"package function self");
  #1;$display("TRACE types %0d",p==q);$finish;
 end
endmodule
