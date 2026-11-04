class Item;static int count=0;int value=1;endclass
module top;
 Item item;string s;int calls=0,stage=0;
 function automatic int mutate();calls++;item.value=42;return 7;endfunction
 function automatic string render(input Item value);return $sformatf("%0p",value);endfunction
 initial begin
  item=new();$swrite(s,item,"/%0d",mutate());$display("TRACE effects <%s> %0d",s,calls);
  s=render(item);$display("TRACE function <%s>",s);
  $sformat(s,"[%p]",item);$display("TRACE formatted <%s>",s);
  $swrite(s,"%p",item);$display("TRACE task <%s>",s);
  stage++;#1;item=null;s=$sformatf("%p",item);$display("TRACE null <%s>",s);$finish;
 end
endmodule
