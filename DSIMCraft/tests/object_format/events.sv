class Item;event ev;static event common;int value=3;endclass
module top;
 Item item;string s;int stage=0;
 initial begin
  item=new();$swrite(s,item);$display("TRACE before <%s>",s);
  ->item.ev;->Item::common;$swrite(s,item);$display("TRACE triggered <%s>",s);
  stage++;#1;$swrite(s,item);$display("TRACE later <%s>",s);$finish;
 end
endmodule
