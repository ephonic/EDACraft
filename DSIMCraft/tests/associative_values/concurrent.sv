module top;
  typedef int map_t[string];
  map_t first,second;
  int observed;
  task automatic collect(output map_t values,input int value,input int delay_value);
    values["key"]=value;
    #(delay_value);
    values["end"]=value+1;
  endtask
  initial begin
    first["old"]=3;second["old"]=4;
    fork
      collect(first,10,2);
      collect(second,20,3);
      begin #1;$display("TRACE concurrent pending %0d %0d",first["old"],second["old"]);end
    join
    observed=first.num()+second.num();
    $display("TRACE concurrent %0d %0d %0d %0d %0d",observed,first["key"],first["end"],second["key"],second["end"]);
  end
endmodule
