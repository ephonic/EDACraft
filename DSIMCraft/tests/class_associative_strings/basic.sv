module top;
 class Key;int id;function new(int n);id=n;endfunction endclass
 class Holder;string rights[Key];endclass
 Holder h;Key a,b,k;int count,total;
 initial begin
  h=new;a=new(3);b=new(5);
  if(h.rights[a]!=""||h.rights[null]!=""||h.rights.num()!=0)$fatal(1,"missing string default");
  if(h.rights[a].len()!=0)$fatal(1,"missing string method");
  h.rights[a]="RW";h.rights[b]="RO";h.rights[null]="NULL";
  if(h.rights[a]!="RW"||h.rights[b]!="RO"||h.rights[null]!="NULL"||h.rights.num()!=3)$fatal(1,"class keys");
  foreach(h.rights[key])begin count++;total+=h.rights[key].len();end
  if(count!=3||total!=8||!h.rights.exists(null)||!h.rights.first(k))$fatal(1,"iteration");
  h.rights.delete(a);if(h.rights.exists(a)||h.rights[a]!="")$fatal(1,"delete");
  $display("TRACE class assoc string %0d %0d",count,total);$finish;
 end
endmodule
