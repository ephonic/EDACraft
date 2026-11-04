module top;
 class Item;int value;endclass
 class Packet;
  local rand Item items[];
  rand Item parent;
  rand int tag;
  constraint legal {tag==29;foreach(items[i])items[i].value==17;}
  function void setup(Item x);items=new[1];items[0]=x;parent=x;endfunction
  function int count();return items.size();endfunction
  function int mode();int off_mode;items.rand_mode(0);items.rand_mode(1);tag.rand_mode(0);off_mode=tag.rand_mode();tag.rand_mode(1);return off_mode==0?tag.rand_mode():-1;endfunction
 endclass
 Packet p;Item x;int observed;
 initial begin
  p=new;x=new;x.value=17;p.setup(x);p.tag=29;
  if(p.mode()!=1||p.count()!=1||!p.randomize(null))$fatal(1,"declared random handle state check");
  p.tag=0;if(!p.randomize(tag)||p.tag!=29||x.value!=17)$fatal(1,"selected scalar preserves handle state");
  x.value=18;if(p.randomize(null)||p.tag!=29||x.value!=18)$fatal(1,"state constraint unsat");
  observed=p.tag;
  $display("TRACE random handle declarations scalar selection state constraints pass");$finish;
 end
endmodule
