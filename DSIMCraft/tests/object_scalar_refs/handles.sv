module top;
 typedef enum {ONE,TWO} kind_t;
 class Item;int id;endclass
 class State;Item item;kind_t kind=ONE;endclass
 State state;Item item;int observed;
 function automatic void update(ref Item target,ref kind_t kind,input Item source);target=source;kind=TWO;endfunction
 initial begin state=new;item=new;item.id=17;update(state.item,state.kind,item);observed=state.item.id;
  $display("TRACE handles %0d %0d %0d",observed,state.item==item,state.kind);
 end
endmodule
