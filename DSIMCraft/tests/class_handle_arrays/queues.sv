module top;
 typedef enum int {LOW=-3,HIGH=11} word_t;
 class Packet;
  rand bit [7:0] q[$];
  rand bit [7:0] bounded[$:3];
  rand word_t labels[$];
  rand int length;
  bit [7:0] other[$];
  constraint sizes {q.size() inside {[2:4]};bounded.size()==q.size()-1;labels.size()==q.size();length==q.size();}
  constraint elements {foreach(q[i])q[i]==i+9;foreach(bounded[i])bounded[i]==i+17;foreach(labels[i])labels[i]==((i%2)?HIGH:LOW);}
 endclass
 Packet p;int observed;
 initial begin
  p=new;
  repeat(8)begin
   if(!p.randomize())$fatal(1,"queue draw");
   if(p.q.size()!=p.length||p.bounded.size()!=p.length-1||p.labels.size()!=p.length)$fatal(1,"queue coupled sizes");
   foreach(p.q[i])if(p.q[i]!=i+9||p.labels[i]!==((i%2)?HIGH:LOW))$fatal(1,"queue elements and enum domain");
  end
  p.q.rand_mode(0);if(!p.randomize()||p.q[0]!=9)$fatal(1,"disabled queue");
  if(!p.randomize(other) with {other.size()==2;foreach(other[i])other[i]==i+23;})$fatal(1,"selected ordinary queue");
  if(p.other.size()!=2||p.other[1]!=24||p.q[0]!=9)$fatal(1,"selected queue result");
  observed=p.length;
  $display("TRACE random queues sizes bounded enums modes selected properties pass");$finish;
 end
endmodule
