`timescale 1ps/1ps
module leaf #(parameter W=65);
 typedef class Reporter;
 function automatic int invoke();Reporter r;r=new;return r.value();endfunction
 function automatic string label();Reporter r;r=new;return $sformatf("value=%0d",r.value());endfunction
 // Both legacy integer and typed variables, nested calls and wide conversion.
 integer legacy=invoke();
 int typed=invoke()+3;
 logic [W-1:0] wide=invoke();
 string text=label();
 typedef class Handler;
 class Reporter;
  Handler h;
  function int value();h=new;return h.n;endfunction
 endclass
 class Handler;int n=19;endclass
 initial begin
  #1;$display("TRACE runtime %0d %0d %0d %0d %s",W,legacy,typed,wide,text);
 end
endmodule
module top;leaf #(65) one();leaf #(129) two();endmodule
