module top;
  reg [7:0] i,j,q,count,once;
  initial begin
    q=0;
    for(i=0;i<5;i=i+8'd1)
      for(j=0;j<3;j=j+8'd1) q=q+8'd3;
    $display("TRACE for q=%0d i=%0d j=%0d",q,i,j);
    while(q<50) q=q+8'd1;
    do q=q+8'd1; while(1'b0);
    once=0;
    while(1'bx) once=once+8'd1;
    do once=once+8'd1; while(1'bx);
    $display("TRACE while q=%0d once=%0d",q,once);
    count=3;
    repeat(count) begin
      count=0;
      repeat(2) q=q+8'd1;
    end
    repeat(0) q=0;
    repeat(4'b0x01) q=0;
    repeat(4'bzzzz) q=0;
    for(i=0;i<3;i=i+8'd1) ;
    if(1) repeat(2) q=q+8'd1;
    else q=0;
    $display("TRACE repeat q=%0d count=%0d i=%0d",q,count,i);
    $finish;
  end
endmodule
