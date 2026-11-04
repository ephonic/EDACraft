module top;
 class Item;int id;function new(int n);id=n;endfunction endclass
 typedef struct {string name;bit[7:0] flags;logic[3:0] state;Item item;} Entry;
 typedef struct {Entry entry;string label;} Record;
 class Base;Record data;endclass
 class Child extends Base;endclass
 Child a,b,alias_a;Item item;int observed;
 initial begin
  a=new;b=new;alias_a=a;
  if(a.data.entry.name!=""||a.data.label!=""||a.data.entry.flags!==0||a.data.entry.state!==4'bxxxx||a.data.entry.item!=null)$fatal(1,"object defaults");
  item=new(5);a.data.entry.name="alpha";a.data.label="outer";a.data.entry.flags='x;a.data.entry.state=4'b10xz;a.data.entry.item=item;
  b.data=a.data;b.data.entry.name="beta";b.data.label="copy";b.data.entry.flags[3:0]=4'h7;
  if(alias_a.data.entry.name!="alpha"||a.data.label!="outer"||b.data.entry.name!="beta"||a.data.entry.flags!==0||b.data.entry.flags!==7||b.data.entry.state!==4'b10xz)$fatal(1,"object copy fields");
  if(b.data.entry.item.id!=5)$fatal(1,"nested class handle");
  observed=b.data.entry.flags+b.data.entry.item.id;$display("TRACE struct scalar %0d",observed);$finish;
 end
endmodule
