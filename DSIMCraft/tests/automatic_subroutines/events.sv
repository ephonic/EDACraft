`timescale 1ns/1ps
module top;
logic clk=0;
integer a=0,b=0,qa=0,qb=0,idx=0,word=0;
logic[127:0] bank=0;
task automatic wait_edge(input integer x,output integer y);
 integer local_value=x+1;
 begin @(posedge clk);y=local_value;end
endtask
function automatic integer sample(input integer x,output logic[31:0] y=bank[idx++*32+:32]);
 integer local_value=x+2;
 begin idx=2;y=local_value;return local_value+1;end
endfunction
initial begin #2 clk=1;#1 clk=0;#2 clk=1;end
initial begin wait_edge(3,a);if(a!==4)$fatal(1,"first event frame");end
initial begin #1;wait_edge(9,b);if(b!==10)$fatal(1,"second event frame");end
initial begin
 #3 if(a!==4||b!==10)$fatal(1,"overlap event copy");
 qa<=#2 sample(5);
 if(qa!==0||idx!==3||bank[95:64]!==7)$fatal(1,"automatic delayed NBA capture");
 qb=#1 sample(8);
 if(qb!==11||idx!==3||bank[95:64]!==10)$fatal(1,"automatic blocking capture");
 #2 if(qa!==8)$fatal(1,"automatic NBA delivery");
 $display("TRACE events complete");
end
endmodule
