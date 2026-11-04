class Event;
 event pulse;
 function void copy(Event rhs);pulse=rhs.pulse;endfunction
endclass
module top;
 Event a,b,saved;int old_hits=0,new_hits=0,stage=0;
 initial begin
  a=new();b=new();saved=new();saved.copy(a);
  fork
   begin @(a.pulse);old_hits++;end
   begin @(b.pulse);new_hits++;end
   begin #1;a.copy(b);->a.pulse;#1;
    $display("TRACE alias %0d %0d",old_hits,new_hits);->saved.pulse;
   end
  join
  stage++;#1;$display("TRACE captured %0d %0d",old_hits,new_hits);$finish;
 end
 initial begin #10;$fatal(1,"lost event alias");end
endmodule
