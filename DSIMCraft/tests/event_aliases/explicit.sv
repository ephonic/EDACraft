module top;
 int hits=0,stage=0;
 initial begin
  automatic event pulse;
  fork begin @(pulse);hits++;end begin #1;->pulse;end join
  stage++;#1;$display("TRACE explicit %0d",hits);$finish;
 end
endmodule
