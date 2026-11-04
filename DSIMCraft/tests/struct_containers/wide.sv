module top;
 typedef struct {bit[128:0] bits;string name;logic[64:0] state;} Entry;
 class Store #(type T=Entry);T q[$:2];T scalar;endclass
 Store #(Entry) store,copy;Entry v;int observed;
 initial begin
  store=new;copy=new;
  if(store.scalar.bits!==0||store.scalar.name!=""||store.scalar.state!==65'bx)$fatal(1,"wide object defaults");
  v='{bits:129'h100000000000000000000000000000007,name:"wide",state:65'h10000000000000003};store.q.push_back(v);store.q[0].bits[127:64]=64'hfedcba9876543210;
  copy.q=store.q;store.q[0].name="changed";store.q[0].bits[7:0]='x;
  if(copy.q[0].name!="wide"||copy.q[0].bits[128]!==1'b1||copy.q[0].bits[127:64]!==64'hfedcba9876543210||store.q[0].bits[7:0]!==0||copy.q[0].state!==65'h10000000000000003)$fatal(1,"wide selected stores");
  observed=copy.q[0].bits[7:0];$display("TRACE struct wide %0d",observed);$finish;
 end
endmodule
