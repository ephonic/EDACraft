`timescale 1ps/1ps
module top;
 typedef process proc_t;
 proc_t parent,alias_handle;
 string saved;int unsigned first,again;int passed,calls;
 class C;rand int data;endclass
 C object;
 function automatic proc_t here();return proc_t::self();endfunction
 function automatic proc_t receiver();calls++;return parent;endfunction
 function automatic int seed();calls++;return 123;endfunction
 task automatic check_self(input proc_t expected);
  if(process::self()!=expected||here()!=expected)$fatal(1,"nested identity");
 endtask
 initial begin
  parent=process::self();alias_handle=here();check_self(parent);
  if(parent==null||alias_handle!=parent)$fatal(1,"process identity");
  receiver().srandom(seed());if(calls!=2)$fatal(1,"actual evaluation count");saved=parent.get_randstate();
  alias_handle=process::self();check_self(parent);
  if(saved!=parent.get_randstate())$fatal(1,"self consumed random state");
  first=$urandom();parent.set_randstate(saved);again=$urandom();
  if(first!=again)$fatal(1,"restore");
  alias_handle.srandom(123);if(first!=$urandom())$fatal(1,"srandom stream");
  saved=parent.get_randstate();object=new;void'(object.randomize());
  parent.set_randstate(saved);first=$urandom();parent.set_randstate(saved);
  if(first!=$urandom())$fatal(1,"object isolation");
  passed=1;#1;$display("TRACE random %0d",passed);$finish;
 end
endmodule
