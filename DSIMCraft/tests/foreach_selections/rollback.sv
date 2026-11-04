`timescale 1ps/1ps
module top;
 class Map;int values[int];endclass
 Map maps[2];
 int observed;
 task automatic sample(input int which,output int result);
  result=0;
  foreach(maps[which].values[key])begin
   #0;result+=maps[which].values[key];
  end
 endtask
 initial begin
  maps[0]=new;maps[1]=new;maps[0].values[1]=1;
  sample(0,observed);
  #2;maps[0].values[2]=2;sample(0,observed);
  #1;maps[1].values[-1]=9;sample(1,observed);
  #2;if(observed!=9)$fatal(1,"restored selected foreach");
  $display("TRACE foreach selections rollback=%0d",observed);$finish;
 end
endmodule
