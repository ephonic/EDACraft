module top;
 class Cell;int value=7;function void bump();value++;endfunction endclass
 const Cell saved=new;
 int observed;
 initial begin saved.bump();observed=saved.value;if(observed!=8)$fatal(1,"mutable const pointee");
 #1;$display("TRACE const handle %0d",observed);$finish;end
endmodule
