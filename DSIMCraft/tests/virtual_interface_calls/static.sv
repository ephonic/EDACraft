interface bus_if;
 function integer next();integer calls=0;calls++;return calls;endfunction
endinterface
module top;
 bus_if a(),b();virtual bus_if vif;integer values[0:3];
 initial begin vif=a;values[0]=vif.next();vif=b;values[1]=vif.next();vif=a;values[2]=vif.next();vif=b;values[3]=vif.next();
  if(values[0]!=1||values[1]!=1||values[2]!=2||values[3]!=2)$fatal(1,"static instance storage");
  $display("TRACE vif static %0d %0d %0d %0d",values[0],values[1],values[2],values[3]);
 end
endmodule
