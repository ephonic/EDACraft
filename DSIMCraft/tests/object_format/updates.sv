class Item;static int count=1;int value=2;endclass
module top;
 Item item;string rendered;int stage=0;
 always @(stage) $swrite(rendered,item);
 initial begin
  #1;item=new();stage++;#1;$display("TRACE initial <%s>",rendered);
  Item::count=9;stage++;#1;$display("TRACE static <%s>",rendered);
  item.value=7;stage++;#1;$display("TRACE member <%s>",rendered);$finish;
 end
endmodule
