`timescale 1ps/1ps
module top;
 process parent,child;string own_state,child_state;int unsigned first,again;int passed;
 initial begin
  parent=process::self();
  fork begin
   child=process::self();#2;first=$urandom();#2;again=$urandom();
  end join_none
  #1;own_state=parent.get_randstate();
  child.srandom(311);child_state=child.get_randstate();
  if(parent.get_randstate()!=own_state)$fatal(1,"target seed changes caller");
  #2;child.set_randstate(child_state);wait fork;
  if(first!=again)$fatal(1,"target restore");
  if(parent.get_randstate()!=own_state)$fatal(1,"target restore changes caller");
  passed=1;$display("TRACE target %0d",passed);$finish;
 end
endmodule
