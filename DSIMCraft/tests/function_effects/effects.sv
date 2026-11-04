`timescale 1ns/1ps
module top;
integer calls=0,total=0,out=0,io=2,q=0,ret=0,i=0;
logic[15:0] bits=0;integer pos=0;
function integer bump(input integer x,output integer y,inout integer z);
 begin calls++;total+=x;y=x+10;z+=x;return total;end
endfunction
function integer part(input integer x);
 begin bits[pos+:4]=x;pos+=4;return pos;end
endfunction
initial begin
 #1 q<=#3 bump(3,out,io);
 if(calls!==1||total!==3||out!==13||io!==5||q!==0)$fatal(1,"NBA immediate effects");
 #1 if(calls!==1||q!==0)$fatal(1,"NBA pending");
 #3 if(q!==3||calls!==1||io!==5)$fatal(1,"NBA single evaluation");
 ret=0&&bump(100,out,io);ret=1||bump(100,out,io);
 if(calls!==1)$fatal(1,"logical short circuit");
 ret=(i++==0)?bump(2,out,io):bump(100,out,io);
 if(ret!==5||calls!==2||i!==1||out!==12||io!==7)$fatal(1,"conditional effects");
 ret=part(3)+part(5);if(ret!==12||bits!==16'h0053||pos!==8)$fatal(1,"ordered partial effects");
 q=#2 bump(4,out,io);
 if(calls!==3||total!==9||q!==9||out!==14||io!==11)$fatal(1,"blocking delay snapshot");
 $display("TRACE effects complete");
end
endmodule
