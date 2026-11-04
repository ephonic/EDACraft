module top;
 int count,observed;
 typedef int number_t;
 function void tick; count++; count+=2; endfunction:tick
 function empty; endfunction
 function one; one=1; endfunction
 function [8:0] packed_value; packed_value=9'h1a3; endfunction
 function automatic [8:0] auto_packed; return 9'h19b; endfunction
 function automatic implicit_auto; return 1; endfunction
 function int signed_value; return -7; endfunction
 function automatic int auto_value; return count+4; endfunction
 function static int static_value; return count+5; endfunction
 function number_t named_value; return count+6; endfunction
 function automatic number_t named_auto; return count+7; endfunction
 function unsigned low_bit; return 1; endfunction
 function signed [8:0] signed_packed; return -3; endfunction
 function int old_input;
  input int amount;
  int local_value;
  local_value=amount+1;
  return local_value;
 endfunction
 task automatic add;count++;count+=2;endtask
 initial begin
  tick(); add();
  if(count!=6 || one()!=1 || packed_value()!=9'h1a3 || auto_packed()!=9'h19b || implicit_auto()!=1)$fatal(1,"implicit returns");
  if(signed_value()!=-7 || auto_value()!=10 || static_value()!=11 || named_value()!=12 || named_auto()!=13)$fatal(1,"typed returns");
  if(low_bit()!=1 || signed_packed()!=-3 || old_input(8)!=9)$fatal(1,"non-ANSI compatibility");
  observed=count;#1;$display("TRACE nonansi basic value=%0d",observed);$finish;
 end
endmodule
