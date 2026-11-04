class Box;event pulse;endclass
module top;
 event source;Box box;int edge_hits=0,level_hits=0,stage=0;
 initial begin
  box=new();box.pulse=source;
  fork
   begin @(box.pulse);edge_hits++;end
   begin wait(box.pulse.triggered);level_hits++;end
   begin #1;->source;end
  join
  $display("TRACE module %0d %0d %0d",edge_hits,level_hits,box.pulse.triggered);
  stage++;#1;$finish;
 end
 initial begin #10;$fatal(1,"source dependency not propagated");end
endmodule
