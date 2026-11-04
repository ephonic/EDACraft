module top;
 string s;int n=-7;byte unsigned u=253;int stage=0;
 initial begin
  $swriteh(s,n,u);$display("TRACE hex <%s>",s);
  $swriteb(s,4'd3,4'bxz10);$display("TRACE binary <%s>",s);
  $swriteo(s,8'd15,6'bzzxxxx);$display("TRACE octal <%s>",s);
  $swriteh(s,"%0d/",n,8'd15);$display("TRACE override <%s>",s);
  stage++;#1;$swriteb(s);$display("TRACE empty <%s>",s);$finish;
 end
endmodule
