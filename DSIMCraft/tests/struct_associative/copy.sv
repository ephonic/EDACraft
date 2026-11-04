module top;
 typedef bit[159:0] Key;
 typedef struct {string label;bit[128:0] bits;logic[64:0] state;int n;} Entry;
 class Holder;Entry values[string][Key];endclass
 Entry values[string][Key],copy[string][Key];Holder h;Entry item;Key key;string outer;int total=0;
 initial begin
  h=new;key=(160'b1<<133)|160'h123;
  item='{label:"wide",bits:(129'b1<<128)|129'h27,state:65'bx,n:3};
  values["a"][key]=item;values["b"][4].label="default";values["b"][4].n=5;
  h.values=values;copy=h.values;copy["a"][key].label="copy";copy["a"][key].bits[128:125]=4'hf;
  if(values["a"][key].label!="wide"||h.values["a"][key].bits!==item.bits||copy["a"][key].bits[128:125]!==4'hf)$fatal(1,"deep map copy");
  if(copy["b"][4].bits!==0||copy["b"][4].state!==65'bx)$fatal(1,"copied mixed defaults");
  foreach(copy[i,j])total+=copy[i][j].n;
  if(total!=8)$fatal(1,"nested map iteration");
  h.values["a"]=copy["a"];copy["a"].delete(key);
  if(h.values["a"][key].label!="copy"||!h.values["a"].exists(key)||copy["a"].num()!=0)$fatal(1,"submap ownership");
  if(!values.first(outer)||outer!="a"||!values[outer].first(key)||values[outer][key].n!=3)$fatal(1,"typed cursor");
  $display("TRACE struct copies %0d",total);$finish;
 end
endmodule
