module top;
  reg [7:0] q,r;
  reg [3:0] a,b;
  reg flag;
  reg [63:0] wide;
  initial begin
    q=0; r=0; a=1; b=2; wide=0; flag=0;
    {a,b}<={b,a};
    q[7:4]<=a; q[3:0]<=b; q[5:2]<=4'hf;
    q[0]=1;
    r[7:4]<=a; r[0]=1;
    wide[63]<=1'b1; wide[31:0]<=32'hdeadcafe; wide[62:32]<=31'd5;
    {flag,flag}<=2'b10;
    #0 $display("TRACE inactive q=%h r=%h a=%h b=%h wide=%h",q,r,a,b,wide);
    #1 $display("TRACE committed q=%h r=%h a=%h b=%h wide=%h flag=%b",q,r,a,b,wide,flag);
    q[7:4]<=a; q[3:0]<=b; q<=8'hff; q[0]<=1'b0;
    #1 $display("TRACE ordered q=%h",q);
    $finish;
  end
endmodule
