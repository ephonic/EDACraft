module top;
 class Base #(parameter int W=9);
  typedef struct {string label;bit[W-1:0] flags;logic state;} Entry;
  Entry values[int];Entry plain;
  function void put(int key,string label);values[key].label=label;values[key].flags='x;endfunction
 endclass
 class Child extends Base#(129);int tag=7;endclass
 Base#(9) a,b;Child c;int observed;
 initial begin
  a=new;b=new;c=new;
  a.put(-3,"nine");c.put(5,"wide");b.put(-3,"independent");
  if(a.values[-3].label!="nine"||b.values[-3].label!="independent"||c.values[5].label!="wide")$fatal(1,"template object isolation");
  if(a.values[-3].flags!==0||c.values[5].flags!==0||c.values[8].flags!==0||c.values[8].state!==1'bx)$fatal(1,"inherited metadata");
  if(c.plain.flags!==0||c.plain.label!=""||c.plain.state!==1'bx)$fatal(1,"scalar struct metadata");
  c.values[5].flags[128]=1'b1;if(c.values[5].flags[128]!==1'b1||a.values[-3].flags!==0)$fatal(1,"parameter field layout");
  observed=c.tag+a.values.num()+b.values.num()+c.values.num();$display("TRACE struct classes %0d",observed);$finish;
 end
endmodule
