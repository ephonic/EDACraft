class Box;event pulse;function void copy(Box rhs);pulse=rhs.pulse;endfunction endclass
module top;
 Box a,b,saved;int old_hits=0,new_hits=0,stage=0;
 initial begin
  a=new();b=new();saved=new();saved.copy(a);
  fork
   begin @(saved.pulse);old_hits++;end
   begin @(b.pulse);new_hits++;end
   begin #1;->> #2 a.pulse;a.copy(b);#3;->b.pulse;end
  join
  stage++;#1;$display("TRACE deferred %0d %0d",old_hits,new_hits);$finish;
 end
 initial begin #10;$fatal(1,"deferred event target rebound");end
endmodule
