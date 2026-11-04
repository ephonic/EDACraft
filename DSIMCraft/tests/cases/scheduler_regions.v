module top;
  reg [7:0] a,b,q;
  reg [7:0] observations;
  initial begin
    a=0; b=0; q=0; observations=0;
    #1;
    a<=1; b<=2;
    q[7:4]<=4'ha;
    #0;
    q[3:0]<=4'h5;
    #0 $display("TRACE inactive a=%0d b=%0d q=%h",a,b,q);
    #0 $display("TRACE still_inactive a=%0d b=%0d q=%h",a,b,q);
    #1 $display("TRACE committed a=%0d b=%0d q=%h observations=%0d",a,b,q,observations);
    a<=3; b<=4;
    #1 $display("TRACE second a=%0d b=%0d observations=%0d",a,b,observations);
    $finish;
  end
  always @(a or b) begin
    if(a!=0 || b!=0) begin
      observations=observations+8'd1;
      $display("TRACE batch a=%0d b=%0d q=%h",a,b,q);
    end
  end
endmodule
