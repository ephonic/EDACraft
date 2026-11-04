module top;
 class Store;int data[string][int];endclass
 Store a,b;int data[int][string],copy[int][string];int observed;
 initial begin
 a=new;b=new;a.data["m"][-2]=7;data[-1]["x"]=5;
 #1;copy=data;b.data=a.data;
 #1;a.data["m"][-2]=9;data[-1].delete();data[3]["y"]=6;
 observed=copy[-1]["x"]+b.data["m"][-2];
 #1;observed+=data[3]["y"];
 #1;$display("TRACE rollback %0d %0d %0d %0d",observed,copy.num(),data[-1].num(),b.data["m"][-2]);
 end
endmodule
