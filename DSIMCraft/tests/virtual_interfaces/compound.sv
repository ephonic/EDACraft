interface bus_if;logic signed[15:0] data;int count;endinterface
class holder;virtual bus_if vif;endclass
module top;
 bus_if a(),b();holder h;int calls;logic[3:0] old;
 function automatic holder receiver();calls++;return h;endfunction
 initial begin
  a.data=-8;a.count=0;b.data=0;h=new();h.vif=a;
  receiver().vif.data+=3;
  old=receiver().vif.data[3:0]++;
  a.count++;h.vif=b;h.vif.data=8;h.vif.data>>>=1;
  if(a.data!==-4||b.data!==4||a.count!=1||old!=11||calls!=2)$fatal(1,"compound snapshot");
  $display("TRACE virtual compound %0d %0d %0d %0d %0d",a.data,b.data,a.count,old,calls);
 end
endmodule
