// Receiver side-effect probe; raw call count/target order differences are retained.
interface bus_if;
 integer state=10;
 function automatic integer edit(ref integer item,input integer delta);item+=delta;state+=item;return state;endfunction
endinterface
class holder;virtual bus_if vif;endclass
module top;
 bus_if a(),b();holder h;integer calls=0,item=4,result;
 function automatic holder receiver();calls++;return h;endfunction
 function automatic integer argument_value();h.vif=b;return 2;endfunction
 initial begin h=new();h.vif=a;result=receiver().vif.edit(item,argument_value());
  if(calls<1||item!=6||result!=16||(a.state+b.state)!=26)$fatal(1,"receiver/arguments");
  $display("TRACE vif capture %0d %0d %0d %0d %0d",calls,item,result,a.state,b.state);
 end
endmodule
