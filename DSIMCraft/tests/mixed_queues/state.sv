module top;
 typedef bit[128:0] BQ[$];typedef logic[128:0] LQ[$];
 BQ clean[int];LQ raw[int];int observed;
 function automatic int local_count(input int n);
  int scratch[int][$];
  if(scratch.num()!=0)return -100;
  scratch[n].push_back(n);scratch[n].push_back(n+1);
  return scratch[n][0]+scratch[n][1];
 endfunction
 initial begin
  raw[1]='{129'h100000000000000000000000000000001,'x};
  clean=raw;
  if(clean[1][0]!==129'h100000000000000000000000000000001||clean[1][1]!==0)$fatal(1,"deep two state conversion");
  clean[1][0][127:64]=64'hfedcba9876543210;
  if(clean[1][0][128]!==1'b1||clean[1][0][127:64]!==64'hfedcba9876543210||raw[1][0][127:64]!==0)$fatal(1,"wide copy and slice");
  observed=local_count(2)+local_count(3);
  if(observed!=12)$fatal(1,"automatic activation");
  $display("TRACE mixed state %0d",observed);$finish;
 end
endmodule
