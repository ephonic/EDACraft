module top;
 function integer extern(input integer x);extern=x+3;endfunction
 function integer \C::get (input integer x);\C::get =x+7;endfunction : \C::get 
 function integer \C::new (input integer x);\C::new =x+11;endfunction : \C::new 
 integer observed;
 initial begin
  observed=extern(2);$display("TRACE keyword %0d",observed);
  #1;observed=\C::get (3)+\C::new (5);$display("TRACE escaped %0d",observed);$finish;
 end
endmodule
