module top;
 typedef bit signed [7:0] s8_t;typedef bit [7:0] u8_t;typedef logic [7:0] l8_t;typedef bit [64:0] u65_t;
 typedef bit[31:0] bits_t;int bits_map[bits_t],int_map[int unsigned];
 int a[s8_t],b[u8_t],c[l8_t],d[u65_t];s8_t s;u8_t u;l8_t l;u65_t w;int calls;
 function logic [15:0] index_value();calls++;return 16'h0181;endfunction
 initial begin
  a[index_value()]=9;a[16'h017f]=8;a[s8_t'(8'b1x01z001)]=7;
  b[-1]=3;b[511]=4;c[16'h0101]=6;c[16'hxx01]=8;d[-1]=10;
  int_map[32'h80000000]=12;bits_map=int_map;int_map.delete();int_map=bits_map;
  if(bits_map.num()!=1||int_map[32'h80000000]!=12)$fatal(1,"equivalent integral key state types");
  if(calls!=1||a[-127]!=9||a[8'h91]!=7||b.num()!=1||b[255]!=4||c[1]!=8)$fatal(1,"key conversion");
  if(a.first(s))do $display("TRACE narrow signed %0d %0d",s,a[s]);while(a.next(s));
  if(!b.first(u)||u!=255||!c.first(l)||l!=1||!d.first(w)||w!=65'h1ffffffffffffffff)$fatal(1,"key width conversion");
  $display("TRACE key copies %0d %0d",bits_map[32'h80000000],int_map[32'h80000000]);
  $display("TRACE conversions %0d %0d %0d %0h",calls,b[u],c[l],w);
 end
endmodule
