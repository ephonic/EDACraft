module top;
  reg a;
  reg [3:0] b;
  reg [7:0] i,count;
  initial begin
    a=0; b=0;
    repeat(2) begin
      #1 a=1;
      #1 a=0;
      #1 b=4'b1000;
      #1 b=0;
      #1 a=1;
      #1 a=0;
    end
  end
  initial begin
    count=0;
    for(i=0;i<2;i=i+8'd1) begin
      @(posedge a); count=count+8'd1;
      $display("TRACE pos count=%0d t=%0d",count,$time);
      @(b); count=count+8'd1;
      $display("TRACE high_bit count=%0d t=%0d",count,$time);
      @(posedge a or negedge a); count=count+8'd1;
      $display("TRACE either count=%0d t=%0d",count,$time);
      @(negedge a); count=count+8'd1;
      $display("TRACE neg count=%0d t=%0d",count,$time);
    end
    #0 $display("TRACE done count=%0d",count);
    $finish;
  end
endmodule
