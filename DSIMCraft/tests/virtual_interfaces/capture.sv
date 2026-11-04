interface bus_if;logic[7:0] data;endinterface
class holder;virtual bus_if vif;endclass
module top;
 bus_if a(),b();holder h;int index,calls;
 function automatic holder receiver();calls++;return h;endfunction
 initial begin
  a.data=0;b.data=0;h=new();h.vif=a;index=0;
  receiver().vif.data[index+:4]<=4'hb;
  index=4;h.vif=b;
  #1;
  if(a.data!==8'h0b||b.data!==0||calls!=1)$fatal(1,"NBA target snapshot");
  $display("TRACE virtual capture %0h %0h %0d",a.data,b.data,calls);
 end
endmodule
