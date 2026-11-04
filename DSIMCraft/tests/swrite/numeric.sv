module top;
 string s;int n=-7;byte narrow=-3;byte unsigned u=253;logic[7:0] x=8'hxz;real r=1.25;int stage=0;
 initial begin
  $swrite(s,n);$display("TRACE int <%s> %0d",s,s.len());
  $swrite(s,narrow,u,4'd3,x);$display("TRACE nums <%s>",s);
  $swrite(s,130'h3ffffffffffffffffffffffffffffffff);$display("TRACE wide <%s>",s);
  $swrite(s,r);$display("TRACE real <%s>",s);
  $swrite(s,null);$display("TRACE null <%s>",s);
  stage++;#1;$swrite(s);$display("TRACE empty <%s>",s);$finish;
 end
endmodule
