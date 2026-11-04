`timescale 1ns/1ps
interface state_if;
 typedef enum logic[1:0]{A,B,C} state_t;
 typedef struct packed{logic[7:0] hi;logic[3:0] lo;} record_t;
 state_t state=A;record_t record;logic[7:0] cells[0:1][2:3];
 modport rw(output state,record,cells);
 modport ro(input state,record,cells);
endinterface
module mutate(state_if.rw b);
 integer i=0,j=2;
 initial begin b.record.hi=8'h12;b.record.lo=4'ha;b.cells[0][2]=8'h41;b.cells[1][3]=8'h63;
 #1;b.state=b.state.next;b.cells[i][j][3:0]=4'h7;
 #1;i=1;j=3;b.cells[i][j]<=8'h81;b.record.hi[3:0]<=4'h6;b.state<=b.state.next;
 end
endmodule
module observe(state_if.ro b,output logic[7:0] value);
 integer i=0,j=2;
 always @* value=b.cells[i][j];
 initial begin #1.5;if(b.state.name!="B"||b.record!==12'h12a||value!==8'h47)$fatal(1,"FAIL aggregate first");
 #1;i=1;j=3;#0.1;if(b.state.name!="C"||b.record!==12'h16a||value!==8'h81)$fatal(1,"FAIL aggregate indexed");
 $display("TRACE aggregates %s %h %h",b.state.name,b.record,value);end
endmodule
module top;
 state_if bus();wire[7:0] seen;mutate m(bus);observe o(bus,seen);
 initial begin #3.5;$finish;end
endmodule
