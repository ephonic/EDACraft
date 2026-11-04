module top;
 class Callback;
  int id;
  function new(int value);id=value;endfunction
  virtual function int get_inst_id();return id;endfunction
 endclass
 Callback a,b,c;
 Callback callbacks[$],selected[$];
 int observed;
 initial begin
  a=new(7);b=new(9);c=new(7);
  callbacks.push_back(a);callbacks.push_back(b);callbacks.push_back(c);callbacks.push_back(a);
  selected=callbacks.unique(cb_) with(cb_.get_inst_id);
  if(selected.size()!=2 || selected[0].get_inst_id()+selected[1].get_inst_id()!=16)$fatal(1,"unique class key");
  selected=callbacks.find(item_) with(item_.get_inst_id()==7);
  if(selected.size()!=3)$fatal(1,"class find result");
  observed=selected.size();#1;$display("TRACE locators classes count=%0d",observed);$finish;
 end
endmodule
