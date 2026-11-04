module top;
 class Item; int value=9; endclass
 Item item;
 chandle opaque;
 function automatic int empty_item();return item==null;endfunction
 function automatic int empty_opaque();return opaque===null;endfunction
 function automatic int choose_item();return (item==null)?7:item.value;endfunction
 int before_item=empty_item();
 int before_opaque=empty_opaque();
 initial begin
  if(before_item!=1||before_opaque!=1||choose_item()!=7)$fatal(1,"null startup");
  item=new;
  if(empty_item()!=0||empty_opaque()!=1||choose_item()!=9)$fatal(1,"runtime handles");
  $display("TRACE handles %0d %0d %0d %0d",before_item,before_opaque,empty_item(),choose_item());
  $finish;
 end
endmodule
