class Item;string text="a%0d";endclass
module top;
 Item item;string s,fmt="[%p]";int stage=0;
 initial begin
  item=new();$swrite(s,item);$display("TRACE literal <%s>",s);
  $sformat(s,fmt,item);$display("TRACE dynamic <%s>",s);
  stage++;#1;item.text="b%h";s=$sformatf(fmt,item);$display("TRACE changed <%s>",s);$finish;
 end
endmodule
