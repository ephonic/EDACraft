module top;
 class Key;int id=7;endclass
 typedef struct {bit[128:0] flags;logic[64:0] state;Key owner;} Plain;
 class Holder;Plain values[Key];Plain scalar;endclass
 Holder h,copy;Key a,b,key;Plain value;int total=0;
 initial begin
  h=new;copy=new;a=new;b=new;b.id=9;
  value=h.values[null];
  if(value.flags!==0||value.state!==65'bx||value.owner!=null||h.values.num()!=0)$fatal(1,"plain struct defaults");
  if(h.scalar.flags!==0||h.scalar.state!==65'bx||h.scalar.owner!=null)$fatal(1,"plain scalar defaults");
  h.values[a].owner=a;h.values[b].owner=b;h.values[a].flags='z;
  if(h.values[a].flags!==0||h.values[a].state!==65'bx)$fatal(1,"plain struct mask");
  copy.values=h.values;copy.values[a].flags[128]=1'b1;
  if(h.values[a].flags!==0||copy.values[a].flags[128]!==1'b1||copy.values[b].owner!=b)$fatal(1,"plain copy");
  foreach(copy.values[k])total+=copy.values[k].owner.id;
  if(total!=16||!h.values.first(key)||!h.values.exists(key))$fatal(1,"class keys");
  $display("TRACE struct handles %0d",total);$finish;
 end
endmodule
