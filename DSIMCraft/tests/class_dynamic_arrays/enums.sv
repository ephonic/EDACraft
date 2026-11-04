module top;
 typedef enum logic [95:0] {LOW=96'h2,HIGH=96'hfedcba987654321000000005} wide_t;
 class Packet;
  rand wide_t data[];
  rand bit [2:0] position;
  constraint sizes {data.size()==3;position<data.size();}
  constraint values_c {data[position]==HIGH;foreach(data[i])if(i!=position)data[i]==LOW;}
 endclass
 Packet p;int observed;
 initial begin
  p=new;
  repeat(6)begin
   if(!p.randomize())$fatal(1,"enum array draw");
   foreach(p.data[i])if(p.data[i]!==((i==p.position)?HIGH:LOW))$fatal(1,"enum array domain or symbolic index");
   observed+=p.position;
  end
  $display("TRACE class dynamic wide enum domain symbolic indices pass");$finish;
 end
endmodule
