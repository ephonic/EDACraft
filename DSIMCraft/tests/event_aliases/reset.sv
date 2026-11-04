class Event;
 event pulse;
 function void reset();event fresh;pulse=fresh;endfunction
 function void copy(Event rhs);pulse=rhs.pulse;endfunction
endclass
module top;
 Event a,saved;int old_hits=0,new_hits=0,stage=0;
 initial begin
  a=new();saved=new();saved.copy(a);
  fork
   begin @(a.pulse);old_hits++;end
   begin #1;a.reset();->a.pulse;#1;
    $display("TRACE reset %0d",old_hits);->saved.pulse;
   end
  join
  fork begin @(a.pulse);new_hits++;end begin #1;->a.pulse;end join
  stage++;#1;$display("TRACE handles %0d %0d",old_hits,new_hits);$finish;
 end
 initial begin #10;$fatal(1,"lost reset identity");end
endmodule
