module top;
 typedef struct {string label;int n;bit[3:0] flags;} Entry;
 class Holder;Entry values[string];endclass
 typedef enum logic[7:0] {ONE=1,TWO=2} Code;Code codes[2]='{ONE,TWO};
 Holder h;Entry found[$],value;int sum;string key;
 initial begin
  sum=codes.sum with(int'(item));if(sum!=3)$fatal(1,"mapped enum reduction");
  h=new;h.values["a"]='{label:"first",n:2,flags:4'hf};h.values["b"]='{label:"second",n:7,flags:4'h0};h.values["c"]='{label:"third",n:3,flags:4'h0};
  sum=h.values.sum with(item.n);if(sum!=12)$fatal(1,"mapped reduction");
  found=h.values.find with(item.n>2);if(found.size()!=2||found[0].label!="second"||found[1].label!="third")$fatal(1,"struct locator values");
  found[0].label="queue";if(h.values["b"].label!="second")$fatal(1,"locator copy");
  if(!h.values.first(key)||key!="a"||h.values[key].flags!=4'hf)$fatal(1,"string cursor");
  found.sort with(item.n);if(found[0].n!=3||found[1].n!=7)$fatal(1,"struct queue mapped sort");
  h.values.delete("b");if(h.values.exists("b")||h.values.num()!=2)$fatal(1,"delete");
  value=h.values["b"];if(value.flags!==0||value.label!="")$fatal(1,"deleted defaults");
  $display("TRACE struct methods %0d",sum);$finish;
 end
endmodule
