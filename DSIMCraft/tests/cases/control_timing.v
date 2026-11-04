module top;
  reg clk;
  reg [7:0] q,count,i;
  initial begin clk=0; forever #1 clk=~clk; end
  initial begin
    q=0; count=3;
    repeat(count) begin
      @(posedge clk);
      q<=q+8'd1;
      count=0;
      #0 $display("TRACE inactive q=%0d t=%0d",q,$time);
      #1 $display("TRACE committed q=%0d t=%0d",q,$time);
    end
    for(i=0;i<2;i=i+8'd1) begin #0; q<=q+8'd2; #1; end
    $display("TRACE for q=%0d t=%0d",q,$time);
    do begin #1; q=q+8'd1; end while(q<10);
    $display("TRACE do q=%0d t=%0d",q,$time);
    while(q>8) begin @(negedge clk); q=q-8'd1; end
    $display("TRACE while q=%0d t=%0d",q,$time);
    repeat(2) repeat(2) #0 q=q+8'd1;
    #1 $display("TRACE nested q=%0d t=%0d",q,$time);
    $finish;
  end
endmodule
