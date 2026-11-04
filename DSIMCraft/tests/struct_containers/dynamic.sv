module top;
 typedef struct {string name;bit[7:0] flags;logic[3:0] state;int id;} Entry;
 Entry values[],copy[],queue[$],v;int observed;
 initial begin
  values=new[2];
  if(values[0].name!=""||values[0].flags!==0||values[0].state!==4'bxxxx||values[0].id!==0)$fatal(1,"new defaults");
  values[0]='{name:"first",flags:8'hff,state:4'h3,id:4};values[1]=values[0];values[1].name="second";values[1].flags='x;values[1].flags[3:0]=4'h9;
  copy=new[3](values);values[0].name="changed";
  if(copy[0].name!="first"||copy[1].name!="second"||copy[1].flags!==9||copy[2].name!=""||copy[2].flags!==0||copy[2].state!==4'bxxxx)$fatal(1,"new copy");
  queue=copy;v=queue.pop_back();if(v.name!=""||v.flags!==0||v.state!==4'bxxxx)$fatal(1,"copied default");
  queue.delete();v=queue.pop_front();if(v.name!=""||v.flags!==0||v.state!==4'bxxxx||v.id!==0)$fatal(1,"empty pop default");
  v=values[99];if(v.name!=""||v.flags!==0||v.state!==4'bxxxx)$fatal(1,"invalid index default");
  observed=copy[0].id+copy[1].flags;$display("TRACE struct dynamic %0d",observed);$finish;
 end
endmodule
