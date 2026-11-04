typedef integer pair_t[0:1];
interface bus_if;
 integer bias=4;
 function automatic pair_t values(input integer first);pair_t result;result[0]=first+bias;result[1]=first+1+bias;return result;endfunction
 task automatic swap(ref pair_t data,output pair_t result);integer old;old=data[0];data[0]=data[1];data[1]=old;result=values(data[0]);endtask
endinterface
module top;
 bus_if a();virtual bus_if vif;pair_t data,result;
 initial begin vif=a;data=vif.values(2);vif.swap(data,result);
  if(data[0]!=7||data[1]!=6||result[0]!=11||result[1]!=12)$fatal(1,"array transfer");
  $display("TRACE vif arrays %0d %0d %0d %0d",data[0],data[1],result[0],result[1]);
 end
endmodule
