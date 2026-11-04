module top;
 int old_hits=0,new_hits=0,stage=0;
 task automatic round();
  event first,second,saved;
  saved=first;
  fork
   begin @(first);old_hits++;end
   begin @(second);new_hits++;end
   begin #1;first=second;->first;#1;->saved;end
  join
 endtask
 initial begin round();stage++;#1;$display("TRACE local alias %0d %0d",old_hits,new_hits);$finish;end
 initial begin #10;$fatal(1,"local alias lost");end
endmodule
