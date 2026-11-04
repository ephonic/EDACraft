`timescale 1ps/1ps
module top;
  real observed;
  function automatic real update(real a);return a+0.25;endfunction
  initial begin
    observed=0.5;
    #2;observed=update(observed);
    #1;observed=update(observed);
    #2;observed<=1.25;
    #1;if(observed!=1.25)$fatal(1,"real restored state");
    $display("TRACE rollback value=%0.2f",observed);$finish;
  end
endmodule
