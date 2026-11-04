module top;
  int index=0,calls=0;
  logic[3:0] data[0:1];
  logic[3:0] values[];
  int observed;
  function automatic logic[7:0] source_value();index=1;calls++;return 8'h25;endfunction
  initial begin
    data='{0,0};
    {>>{index[3:0],data[index]}}=source_value();
    observed=index;
    $display("TRACE source order %0d %h %h %0d",index,data[0],data[1],calls);
    values='{1,2,3};
    {<<4{values}}={>>{values}};
    $display("TRACE self snapshot %0d %h %h %h",values.size(),values[0],values[1],values[2]);
  end
endmodule
