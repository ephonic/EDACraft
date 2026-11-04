package keys;
 typedef enum bit [27:0] {ZERO=0,HIGH=1<<18} key_t;
endpackage
module child #(parameter W=65)(output int result);
 typedef bit [W-1:0] key_t;typedef int map_t[key_t];map_t m,n;
 initial begin
  m[key_t'('1)]=W;n=m;m.delete();
  foreach(n[i])begin if($bits(i)!=W||i!=key_t'('1))$fatal(1,"clone index");result=n[i];end
 end
endmodule
module top;
 import keys::*;
 class Pool #(type KEY=int);
  int values[KEY];
  function void put(KEY k,int value);values[k]=value;endfunction
  function int total();int r;foreach(values[i])r+=values[i];return r;endfunction
 endclass
 Pool#(key_t) enums;typedef bit [128:0] wide_t;Pool#(wide_t) wide;
 key_t k,indices[$];wide_t w;int r65,r129;
 child#(65) a(r65);child#(129) b(r129);
 initial begin
  enums=new;wide=new;enums.put(HIGH,11);enums.put(ZERO,22);
  wide.put(129'h100000000000000000000000000000000,44);
  if(!enums.values.first(k)||k!=ZERO||!wide.values.first(w)||$bits(w)!=129)$fatal(1,"class index");
  indices=enums.values.find_index() with (item<20);
  if(indices.size()!=1||indices[0]!=HIGH)$fatal(1,"class enum locator");
  #1;$display("TRACE fields %s %0d %0d %0d %0d",indices[0].name(),enums.total(),wide.total(),r65,r129);
 end
endmodule
