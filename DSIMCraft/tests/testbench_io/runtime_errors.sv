module top;
 int kind=0,n=0,r;string fmt,text;
 initial begin
  void'($value$plusargs("error=%d",kind));
  case(kind)
   1:begin fmt="%q";text=$sformatf(fmt,1);end
   2:begin fmt="%d %d";text=$sformatf(fmt,1);end
   3:begin fmt="%1048577d";text=$sformatf(fmt,1);end
   4:begin fmt="n=%d.tail";r=$value$plusargs(fmt,n);end
   5:begin fmt="n=%d";r=$value$plusargs(fmt,text);end
   6:begin fmt="%";text=$sformatf(fmt);end
  endcase
 end
endmodule
