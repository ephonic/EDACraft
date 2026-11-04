module top;
 class Packet;
  rand byte unsigned data[];
  rand bit [15:0] check_data[];
  rand int length;
  constraint sizes {data.size() inside {[2:5]};check_data.size()==data.size()+1;length==data.size();}
  constraint contents {
   foreach(data[i]) {data[i]==length+i;if(i>0)data[i]>data[i-1];}
   foreach(check_data[j])check_data[j]==length+2*j;
  }
 endclass
 Packet p;int observed;
 initial begin
  p=new;p.srandom(145);
  repeat(12)begin
   if(!p.randomize())$fatal(1,"two stage array constraints");
   if(p.length<2||p.length>5||p.data.size()!=p.length||p.check_data.size()!=p.length+1)$fatal(1,"coupled sizes");
   foreach(p.data[i])if(p.data[i]!=p.length+i)$fatal(1,"array elements");
   foreach(p.check_data[j])if(p.check_data[j]!=p.length+2*j)$fatal(1,"second array elements");
   observed+=p.length;
  end
  $display("TRACE class dynamic size scalar coupling foreach guards pass");$finish;
 end
endmodule
