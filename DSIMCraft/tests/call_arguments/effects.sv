`timescale 1ns/1ps
module top;
integer seq=0,calls=0,base=7,out=0,io=2,q=0,idx=0;
logic[127:0] bank=0;
function integer next();begin seq++;return seq;end endfunction
function integer store(input integer x=next(),output logic[31:0] y=bank[idx++*32+:32],inout integer z=io);
 begin calls++;idx=2;y=x+10;z+=x;return x*2;end
endfunction
task act(input integer x=base,output integer y=out,inout integer z=io);
 begin #2;y=x+20;z+=x;end
endtask
initial begin #6 base=99;end
initial begin
 #1 q<=#3 store();
 if(seq!==1||calls!==1||idx!==3||bank[95:64]!==11||io!==3||q!==0)$fatal(1,"default NBA capture");
 #1 if(q!==0||seq!==1)$fatal(1,"pending default NBA");
 #3 if(q!==2||calls!==1)$fatal(1,"single evaluation");
 act(.z(io),.y(out));
 if(out!==27||io!==10||base!==99)$fatal(1,"default task entry sampling");
 act(.x(next()));if(out!==22||io!==12||seq!==2)$fatal(1,"named task default outputs");
 q=#2 store(.x(3),.y(out));
 if(q!==6||out!==13||io!==15||seq!==2||calls!==2||idx!==2||bank[95:64]!==11)$fatal(1,"default blocking delay");
 $display("TRACE effects complete");
end
endmodule
