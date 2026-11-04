module top;
 typedef enum bit[27:0] {DEFAULT=0,DEEP=1<<16,SHALLOW=1<<17} policy_t;
 typedef enum int {UNSEEN=0,STARTED=1,DONE=2} state_t;
 class Item;int tag;function new(int v=0);tag=v;endfunction endclass
 class Copier;
  state_t states[Item][Item][policy_t];
  function void put(Item rhs,Item lhs,policy_t policy,state_t state);states[rhs][lhs][policy]=state;endfunction
  function int total();int value;foreach(states[r,l,p])begin
   value+=r.tag+l.tag+int'(states[r][l][p]);
  end return value;endfunction
 endclass
 Copier c,d;Item a,b;policy_t p;Item first;int observed;
 initial begin
  c=new;d=new;a=new(3);b=new(7);
  c.put(a,b,DEEP,STARTED);c.put(a,b,DEFAULT,DONE);c.put(b,a,SHALLOW,DONE);
  if(!c.states.first(first)||first!=a)$fatal(1,"object order");
  if(!c.states[a][b].first(p)||p!=DEFAULT)$fatal(1,"enum cursor");
  d.states=c.states;c.states[a][b].delete(DEEP);
  if(d.states[a][b].num()!=2||c.states[a][b].num()!=1)$fatal(1,"copy isolation");
  observed=c.total();
  $display("TRACE uvm shape %0d %0d %s %s",observed,d.total(),p.name(),c.states[a][b][DEFAULT].name());
  d.states[a].delete(b);
  $display("TRACE uvm delete %0d %0d %0d",d.states.num(),d.states[a].num(),d.states.exists(a));
 end
endmodule
