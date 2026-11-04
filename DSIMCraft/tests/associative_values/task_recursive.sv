module top;
  typedef int map_t[int];
  map_t data;
  int observed;
  task automatic update(inout map_t values,input int depth);
    values[depth]=depth+10;
    if(depth>0) update(values,depth-1);
    else #2;
    values[depth]+=100;
  endtask
  initial begin
    data[9]=9;
    fork
      update(data,2);
      begin #1;$display("TRACE recursive pending %0d %0d",data.num(),data[9]);end
    join
    observed=data.num();
    $display("TRACE recursive task %0d %0d %0d %0d %0d",observed,data[0],data[1],data[2],data[9]);
  end
endmodule
