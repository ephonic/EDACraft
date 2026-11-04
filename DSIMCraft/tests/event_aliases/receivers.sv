class Box;event pulse;endclass
module top;
 Box a,b;int lhs_calls=0,rhs_calls=0,hits=0,stage=0;
 function automatic Box left();lhs_calls++;return a;endfunction
 function automatic Box right();rhs_calls++;return b;endfunction
 initial begin
  a=new();b=new();left().pulse=right().pulse;
  fork begin @(a.pulse);hits++;end begin #1;->b.pulse;end join
  stage++;#1;$display("TRACE receivers %0d %0d %0d",lhs_calls,rhs_calls,hits);$finish;
 end
endmodule
