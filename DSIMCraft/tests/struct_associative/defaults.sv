module top;
 class Payload;int value=7;endclass
 typedef struct {string label;bit[7:0] flags;logic[3:0] state;Payload handle;} Inner;
 typedef struct {Inner data;time stamp;bit[128:0] wide;} Entry;
 class Holder;Entry entries[string];endclass
 Entry entries[int],value;Holder h;Payload p;int observed;
 initial begin
  h=new;
  value=entries[4];
  if(value.data.label!=""||value.data.flags!==0||value.data.state!==4'bxxxx||value.data.handle!=null||value.wide!==0||value.stamp!==64'hxxxxxxxxxxxxxxxx)$fatal(1,"module missing defaults");
  value=h.entries["missing"];
  if(value.data.label!=""||value.data.flags!==0||value.data.state!==4'bxxxx||value.data.handle!=null||value.wide!==0)$fatal(1,"class missing defaults");
  if(entries.num()!=0||h.entries.num()!=0)$fatal(1,"reads must not create keys");
  entries[4].data.label="one";entries[4].data.flags='x;entries[4].wide='z;
  if(entries[4].data.flags!==0||entries[4].wide!==0||entries[4].data.state!==4'bxxxx||entries[4].data.handle!=null)$fatal(1,"partial write defaults");
  h.entries["item"].data.state=4'b10xz;h.entries["item"].data.label="class";
  if(h.entries["item"].data.flags!==0||h.entries["item"].data.state!==4'b10xz)$fatal(1,"mixed field states");
  p=new;entries[4].data.handle=p;h.entries["item"].data.handle=entries[4].data.handle;
  if(h.entries["item"].data.handle.value!=7)$fatal(1,"class field type");
  value=entries[4];value.data.label="copy";
  if(entries[4].data.label!="one"||value.data.handle!=p)$fatal(1,"value copy");
  observed=entries.num()+h.entries.num();$display("TRACE struct defaults %0d",observed);$finish;
 end
endmodule
