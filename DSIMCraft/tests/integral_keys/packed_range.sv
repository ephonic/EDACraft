package ranges;
 typedef struct packed {bit[63:0] min,max;int unsigned stride;} range_t;
 typedef range_t alias_t;
endpackage
module top;
 import ranges::*;
 int entries[range_t];int saved[range_t];range_t key,cursor,indices[$];int total,visited;
 typedef bit[159:0] raw_t;raw_t raw_cursor,raw_indices[$];
 initial begin
  key='{64'h100000000,64'h100000100,32'd4};entries[key]=17;
  key='{64'h200000000,64'h200000100,32'd8};entries[key]=23;
  key='{64'h8000000000000000,64'h8000000000000100,32'd16};entries[key]=31;
  if(!entries.first(cursor)||cursor.min!=64'h100000000||cursor.stride!=4)$fatal(1,"first packed key");
  if(!entries.next(cursor)||cursor.min!=64'h200000000||!entries.prev(cursor)||cursor.stride!=4)$fatal(1,"next packed key");
  if(!entries.last(cursor)||cursor.min!=64'h8000000000000000)$fatal(1,"last packed key");
  foreach(entries[i])begin total+=entries[i]+i.stride;visited++;end
  if(total!=99||visited!=3)$fatal(1,"foreach packed key");
  indices=entries.find_index() with(item>20);
  if(indices.size()!=2||indices[0].stride!=8||indices[1].stride!=16)$fatal(1,"packed locator");
  raw_indices=entries.find_index() with(item>20);
  if(raw_indices.size()!=2||raw_indices[1]!==indices[1]||!entries.first(raw_cursor)||!entries.first(cursor)||raw_cursor!==cursor)$fatal(1,"integral cursor and locator");
  if(!entries.last(cursor))$fatal(1,"last cursor restore");
  saved=entries;entries.delete(indices[0]);
  if(saved.num()!=3||entries.num()!=2||entries.exists(indices[0]))$fatal(1,"packed copy");
  #1;$display("TRACE packed range %0d %0d %h %0d",total,indices.size(),cursor.min,saved[indices[0]]);$finish;
 end
endmodule
