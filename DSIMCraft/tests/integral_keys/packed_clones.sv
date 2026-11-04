module lane #(parameter int W=64)(output int observed);
 typedef struct packed {bit[W-1:0] address;bit valid;} key_t;
 class Pool #(type KEY=key_t);
  int entries[KEY][int];
  function void put(KEY key,int value);entries[key][3]=value;endfunction
  function int total();int sum;foreach(entries[k,j])begin
   if($bits(k)!=W+1||!k.valid||k.address!={W{1'b1}}||j!=3)return -100000;
   sum+=entries[k][j];
  end return sum;endfunction
 endclass
 Pool #(key_t) pool;key_t key,cursor;int local_map[key_t],copy[key_t];
 initial begin
  pool=new();key.address='1;key.valid=1;pool.put(key,W);observed=pool.total();
  local_map[key]=W+1;copy=local_map;local_map.delete();
  foreach(copy[i])if(i.address!={W{1'b1}}||!i.valid||$bits(i)!=W+1)$fatal(1,"clone index layout");
  if(!copy.first(cursor)||cursor!==key||copy[cursor]!=W+1)$fatal(1,"clone cursor");
 end
endmodule
module top;
 int a,b,c;lane #(32) u(a);lane #(64) v(b);lane #(128) w(c);
 initial begin #1;if(a!=32||b!=64||c!=128)$fatal(1,"packed key specialization");
  $display("TRACE packed clones %0d %0d %0d",a,b,c);$finish;end
endmodule
