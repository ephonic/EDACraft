class Box;event pulse;endclass
module top;
 Box a,b;int hits=0,stage=0;
 initial begin
  a=new();b=new();a.pulse=null;
  fork begin @(a.pulse);hits++;end join_none
  #1;->a.pulse;->>a.pulse;
  $display("TRACE null %0d",hits);
  a.pulse=b.pulse;->a.pulse;#1;
  stage++;$display("TRACE frozen %0d %0d",hits,b.pulse.triggered);$finish;
 end
endmodule
