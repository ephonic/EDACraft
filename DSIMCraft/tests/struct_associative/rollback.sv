`timescale 1ps/1ps
module top;
 typedef struct {string label;bit[7:0] flags;int n;} Entry;
 class Holder;Entry values[string];endclass
 Holder h;Entry values[int];int observed;
 initial begin
  h=new;values[1]='{label:"initial",flags:8'hff,n:1};h.values["one"]=values[1];
  #2;if(h.values.num()!=1||values.num()!=1||values[1].label!="initial")$fatal(1,"rollback initial state");
  h.values["one"].label="nine";h.values["ghost"].n=9;values[2]=h.values["one"];observed=9;
  #1;h.values.delete("ghost");h.values["one"].label="seven";values[2].label="copy";values[1].flags='x;observed=7;
  if(h.values.num()!=1||values[1].flags!==0||values[2].label!="copy"||h.values["one"].label!="seven")$fatal(1,"rollback final state");
  #2;$display("TRACE struct rollback %0d",observed);$finish;
 end
endmodule
