module top;
 typedef struct packed signed {bit sign;bit[63:0] payload;} signed_t;
 typedef struct packed {bit[63:0] high;bit low;} fields_t;
 typedef union packed {bit[64:0] bits;fields_t fields;} union_t;
 typedef struct packed {fields_t nested;bit[63:0] tail;} nested_t;
 int signed_map[signed_t],unions[union_t],nested[nested_t];
 signed_t s;union_t u,keys[$];nested_t n;int total;
 initial begin
  signed_map[-1]=7;signed_map[0]=11;signed_map[-2]=13;
  if(!signed_map.first(s)||s!=-2||!s.sign)$fatal(1,"signed struct order");
  foreach(signed_map[i])total+=signed_map[i];
  if(!signed_map.last(s)||s!=0)$fatal(1,"signed struct last");
  u.bits=65'h10000000000000001;unions[u]=19;
  keys=unions.find_index() with(item==19);
  if(keys.size()!=1||keys[0].fields.high!=64'h8000000000000000||!keys[0].fields.low)$fatal(1,"union key locator");
  foreach(unions[i])if(i.fields.high!=64'h8000000000000000)$fatal(1,"union key metadata");
  n.nested=u.fields;n.tail=64'h1234;nested[n]=29;
  foreach(nested[i])if(i.nested.high!=u.fields.high||i.tail!=64'h1234||$bits(i)!=129)$fatal(1,"nested key metadata");
  #1;$display("TRACE packed types %0d %h %h %0d",total,keys[0].bits,n.tail,nested[n]);$finish;
 end
endmodule
