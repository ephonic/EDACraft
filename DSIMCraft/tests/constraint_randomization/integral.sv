module top;
 class Packet;
  rand int unsigned a,b;
  int unsigned minimum=10,maximum=20;
  constraint bounds { a inside {[minimum:maximum]}; a%2==0; b==a*3+7; }
 endclass
 class Rare;
  rand bit [63:0] address,data;
  constraint exact { address==64'hacbd13572468ef90; (data^address)==64'h13579bdf2468ace0; }
 endclass
 Packet p;Rare r;int i;bit [31:0] seen;
 initial begin
  p=new;r=new;seen=0;
  if($bits(p.randomize())!=32||$bits(std::randomize(i))!=32)$fatal(1,"randomize return type");
  for(i=0;i<24;i++)begin
   if(!p.randomize())$fatal(1,"satisfiable range");
   if(!(p.a>=10&&p.a<=20&&p.a%2==0&&p.b==p.a*3+7))$fatal(1,"constraint result");
   seen[p.a]=1;
  end
  if($countones(seen)<2)$fatal(1,"randomize always chose the same solution");
  if(!r.randomize()||r.address!=64'hacbd13572468ef90||r.data!=64'hbfea888800004370)$fatal(1,"rare exact solution");
  $display("TRACE constraints integral rare multivariable pass");$finish;
 end
endmodule
