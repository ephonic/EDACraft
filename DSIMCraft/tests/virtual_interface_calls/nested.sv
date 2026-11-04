interface bus_if;
 integer state=3;
 function automatic integer add(input integer x);state+=x;return state;endfunction
 function automatic integer read();return state;endfunction
 task automatic nested(output integer value);integer a;a=read();value=add(a);endtask
endinterface
module top;
 bus_if a(),b();virtual bus_if vif;integer first,second;
 initial begin vif=a;first=vif.add(vif.read());vif=b;vif.nested(second);
  if(first!=6||second!=6||a.state!=6||b.state!=6)$fatal(1,"nested lexical calls");
  $display("TRACE vif nested %0d %0d %0d %0d",first,second,a.state,b.state);
 end
endmodule
