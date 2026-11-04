module top;
 class Key;endclass
 class Store;string entries[Key];endclass
 Store s;Key a,b,c;string selected[$];int total;
 initial begin
  s=new;a=new;b=new;c=new;
  s.entries[a]="alpha";s.entries[b]="beta";s.entries[c]="alpha";
  selected=s.entries.find() with(item.len()==4);
  if(selected.size()!=1||selected[0]!="beta")$fatal(1,"string find");
  selected=s.entries.unique();
  if(selected.size()!=2)$fatal(1,"unique values");
  total=s.entries.sum() with(int'(item.len()));
  if(total!=14)$fatal(1,"mapped sum");
  $display("TRACE class string locator %0d %0d",selected.size(),total);$finish;
 end
endmodule
