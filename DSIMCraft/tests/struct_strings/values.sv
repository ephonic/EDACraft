module top;
  typedef struct {string name;string regex;int count;logic [3:0] state;} entry_t;
  typedef struct {entry_t entry;string label;bit valid;} record_t;
  entry_t a,b;
  record_t r,s;
  int observed;
  initial begin
    if(a.name!=""||a.regex!=""||a.count!==0||a.state!==4'bxxxx)$fatal(1,"defaults");
    a.name="alpha";a.regex="a.*";a.count=17;a.state=4'b10xz;
    b=a;b.name="beta";
    if(a.name!="alpha"||b.name!="beta"||b.count!=17||b.state!==4'b10xz)$fatal(1,"copy isolation");
    if(a===b||a==b)$fatal(1,"string equality");
    b.name="alpha";if(!(a===b)||(a==b)!==1'bx)$fatal(1,"four-state equality");
    a='{name:"gamma",regex:"g.*",count:23,state:4'h9};b=a;
    if(!(a==b))$fatal(1,"pattern equality");
    r.entry=a;r.label="record";r.valid=1;s=r;s.entry.name="delta";
    if(r.entry.name!="gamma"||s.entry.name!="delta"||s.label!="record")$fatal(1,"nested copy");
    if(a.name.len()!=5||a.name.toupper()!="GAMMA")$fatal(1,"string methods");
    observed=a.count+s.entry.count;
    $display("TRACE values %s %s %s %s %0d",a.name,b.regex,s.entry.name,s.label,observed);
    #1;$finish;
  end
endmodule
