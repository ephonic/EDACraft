`timescale 1ps/1ps
module top;
 typedef struct {string name;int id;} Entry;
 class Holder;Entry value;Entry queue[$];endclass
 Holder holder;Entry values[];int observed;
 initial begin
  holder=new;holder.value='{name:"initial",id:1};holder.queue.push_back(holder.value);values=new[1];values[0]=holder.value;
  #2;holder.value.name="nine";holder.value.id=9;holder.queue[0]=holder.value;values[0]=holder.value;observed=9;
  if(holder.queue[0].name!="nine"||values[0].id!=9)$fatal(1,"prediction initial values");
  #1;holder.value.name="seven";holder.queue[0].name="queue";values[0].name="dynamic";holder.value.id=7;observed=7;
  if(holder.queue[0].id!=9||values[0].id!=9||holder.value.name!="seven"||holder.queue[0].name!="queue"||values[0].name!="dynamic")$fatal(1,"prediction copy isolation");
  #2;$display("TRACE struct rollback %0d",observed);$finish;
 end
endmodule
