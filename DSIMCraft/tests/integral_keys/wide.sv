module top;
 typedef bit [128:0] wide_t;typedef logic signed [64:0] signed_t;typedef longint unsigned u64_t;
 int wide[wide_t],signed_map[signed_t],unsigned_map[u64_t];wide_t k,found[$];signed_t s;u64_t u;int count;
 initial begin
  wide[129'h100000000000000000000000000000000]=3;wide[129'h100000001]=2;wide[1]=1;
  if(wide.first(k))do begin
    $display("TRACE wide %0h %0d",k,wide[k]);count++;
  end while(wide.next(k));
  if(count!=3||$bits(k)!=129)$fatal(1,"wide key collision");
  found=wide.find_index() with (item>=2);
  if(found.size()!=2||found[0]!=129'h100000001||found[1]!=129'h100000000000000000000000000000000)$fatal(1,"wide locator");
  signed_map[-2]=10;signed_map[-1]=20;signed_map[0]=30;signed_map[65'hffffffffffffffff]=40;
  if(signed_map.first(s))do $display("TRACE wide signed %0d %0d",s,signed_map[s]);while(signed_map.next(s));
  unsigned_map[64'hffffffffffffffff]=5;unsigned_map[1]=6;unsigned_map[64'h8000000000000000]=7;
  if(unsigned_map.first(u))do $display("TRACE unsigned %0h %0d",u,unsigned_map[u]);while(unsigned_map.next(u));
  foreach(wide[i])if($bits(i)!=129||wide[i]<1)$fatal(1,"wide foreach");
 end
endmodule
