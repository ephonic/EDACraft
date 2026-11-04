`timescale 1ps/1ps
module top;
 typedef enum bit [27:0] {DEFAULT=0,DEEP=1<<16} key_t;
 typedef bit [128:0] wide_t;
 class Store;int values[key_t];int wide[wide_t];endclass
 Store store;int values[key_t],saved[key_t],wide[wide_t];key_t k;int observed;
 initial begin
  store=new;values[DEFAULT]=3;store.values[DEEP]=4;wide[129'h100000001]=5;store.wide[129'h100000000000000000000000000000000]=6;
  saved=values;observed=7;
  #2;values.delete(DEFAULT);values[DEEP]=9;store.values[DEFAULT]=6;store.values.delete(DEEP);
  wide[1]=11;store.wide[129'h100000000000000000000000000000000]=12;observed=15;
  #1;values[DEFAULT]=2;observed=values[DEEP]+store.values[DEFAULT]+saved[DEFAULT];
  #2;if(values.num()!=2||wide.num()!=2||store.values.exists(DEEP)||store.wide[129'h100000000000000000000000000000000]!=12)$fatal(1,"restored keys");
  if(!values.first(k)||k!=DEFAULT)$fatal(1,"enum order");
  $display("TRACE rollback %s %0d %0d",k.name(),observed,wide[1]);$finish;
 end
endmodule
