module top;
 int seen=0;
 task automatic edit(ref int items[int],input int value);#1;items[value]=value+1;endtask
 task automatic owner(input int value);int local_map[int];local_map[0]=value;edit(local_map,value);seen+=local_map[value];if(local_map.num()!=2)$fatal(1,"automatic map lost");endtask
 initial begin fork owner(3);owner(8);join $display("TRACE sum %0d",seen);end
 endmodule
