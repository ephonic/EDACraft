`timescale 1ps/1ps
module top;
 typedef struct packed {bit[127:0] address;bit valid;} key_t;
 class Store;int entries[key_t];endclass
 Store store;int entries[key_t],saved[key_t];key_t key,other,cursor,keys[$];int observed;
 initial begin
  store=new();key.address=128'h80000000000000000000000000000000;key.valid=1;
  other.address=128'h10000000000000000;other.valid=1;
  entries[key]=3;store.entries[other]=4;saved=entries;observed=7;
  #2;entries.delete(key);entries[other]=9;store.entries[key]=6;store.entries.delete(other);observed=15;
  #1;entries[key]=2;observed=entries[other]+store.entries[key]+saved[key];
  #2;keys=entries.find_index() with(item>2);
  if(entries.num()!=2||store.entries.exists(other)||keys.size()!=1||keys[0]!==other||observed!=18)$fatal(1,"restored packed keys");
  if(!entries.first(cursor)||cursor!==other||!cursor.valid)$fatal(1,"restored packed cursor");
  $display("TRACE packed rollback %0d %h %0d",observed,cursor.address,saved[key]);$finish;
 end
endmodule
