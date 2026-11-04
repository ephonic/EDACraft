module top;
 int kind,n,a;string s;
 initial begin
  if(!$value$plusargs("error=%d",kind))$fatal(1,"missing error");
  case(kind)
   1:n=$sscanf("1.2","%f",a);
   2:n=$sscanf("12","%d%d",a);
   3:n=$sscanf("12","%d",s);
   4:n=$sscanf("12","",a);
   5:n=$sscanf("12","%1048577d",a);
   6:n=$fscanf(123,"%d",a);
   7:n=$sscanf("12","%d%",a);
  endcase
 end
endmodule
