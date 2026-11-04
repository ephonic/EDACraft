module top;
  reg [7:0] q;
  reg [3:0] a,b,overlap;
  reg [15:8] shifted;
  reg flag;
  reg [63:0] wide;
  initial begin
    q=8'h96;
    {q[3:0],q[7:4]}=q;
    $display("TRACE swap=%h",q);
    q[7:4]=4'bxz10; q[0]=1'b1;
    shifted=0; shifted[15:12]=4'ha; shifted[11:8]=4'h5;
    {a,{b[1:0],b[3:2]}}=8'hd6;
    flag=0; {flag,flag}=2'b10;
    overlap=0; {overlap[2:1],overlap[1:0]}=4'b1100;
    $display("TRACE q=%b shifted=%h a=%h b=%h flag=%b overlap=%b",q,shifted,a,b,flag,overlap);
    {a,b}=4'hf+4'h1;
    $display("TRACE context=%h%h",a,b);
    {a,b}='1;
    wide=0; {wide[63],wide[0]}=2'b10; wide[62:1]=62'd1;
    $display("TRACE fill=%h%h wide=%h",a,b,wide);
    $finish;
  end
endmodule
