module top;
 typedef enum logic[67:0] {LOW=2,ALL='1} State;
 State states[string],copy[string];State current;string key;int ok;
 initial begin
  states["all"]=ALL;states["low"]=LOW;copy=states;states.delete();
  current=copy["all"];ok=copy.first(key);
  $display("TRACE enum %s %s %0d %0d",current.name(),copy["low"].name(),ok,copy.num());
  current=copy["absent"];$display("TRACE enum-missing %b %0d",current,copy.size());
  $finish;
 end
endmodule
