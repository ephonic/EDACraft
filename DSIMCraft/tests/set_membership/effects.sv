`timescale 1ns/1ps
module top;
integer count=0,source_value=3,low=1,high=5;
logic first=0,second=0,delayed=0,sampled=0,decoded;
logic[3:0] code=0,mask_value=4'b1?01;
function automatic integer choose();begin count++;return source_value;end endfunction
always_comb decoded=code inside {mask_value,[2:4]};
initial begin
 #1 first=choose() inside {[low:high]};if(first!==1||count!==1)$fatal(1,"selector once");
 second=(choose()==?3);if(second!==1||count!==2)$fatal(1,"wild equality once");
 delayed<=#3 (choose() inside {3});
 sampled=#2 (choose() inside {[0:4]});
 if(sampled!==1||delayed!==0||count!==4)$fatal(1,"delayed sampling");
 #2 if(delayed!==1)$fatal(1,"NBA membership delivery");
 $display("TRACE effects %0d",count);
end
initial begin #2 code=9;#2 mask_value=4'b0?01;#2 code=3;#2 code=15;end
initial begin #1 if(decoded!==0)$fatal(1,"initial comb");#2 if(decoded!==1)$fatal(1,"comb match");#2 if(decoded!==0)$fatal(1,"set dependency");#2 if(decoded!==1)$fatal(1,"range comb");#2 if(decoded!==0)$fatal(1,"comb miss");end
endmodule
