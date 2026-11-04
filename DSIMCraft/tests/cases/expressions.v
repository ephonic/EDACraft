module top;
  reg [7:0] a,b;
  reg [3:0] x,z;
  initial begin
    a=8'hf0;b=8'd3;x=4'bx001;z=4'bz000;
    #1 $display("TRACE add=%0d sub=%0d mul=%0d div=%0d mod=%0d shl=%h shr=%h",a+b,a-b,a*b,a/b,a%b,a<<b,a>>b);
    $display("TRACE cmp=%b%b%b%b logic=%b%b%b red=%b%b%b inv=%b",a<b,a>b,a<=b,a>=b,x&&z,x||z,!z,&x,|x,^x,~z);
    $display("TRACE equal=%b case=%b unequal=%b",x==z,x===z,x!==z);
    $finish;
  end
endmodule
