module top;
  typedef int row_t[int];
  row_t data[string];
  int observed;
  function automatic int update(inout row_t row);
    row[1]+=3;row[2]=9;return row.num();
  endfunction
  initial begin
    data["row"][1]=7;data["other"][5]=15;
    observed=update(data["row"]);
    $display("TRACE subarray %0d %0d %0d %0d %0d",observed,data["row"][1],data["row"][2],data["other"][5],data.num());
  end
endmodule
