class Item;
 static int count=8;
 int signed_value=-3;byte unsigned byte_value=250;
 logic[7:0] x=8'hxz;bit flag=1;bit signed[7:0] negative=-1;
 typedef enum int{FIRST,SECOND} mode_t;mode_t mode=SECOND;
 real value=1.25;string text="a\"\\";
endclass
module top;
 Item item;string s;int stage=0;
 initial begin
  $swrite(s,item);$display("TRACE null <%s>",s);
  item=new();$swrite(s,item);$display("TRACE item <%s>",s);
  stage++;#1;Item::count=9;item.signed_value=-7;$swriteh(s,item);$display("TRACE update <%s>",s);$finish;
 end
endmodule
