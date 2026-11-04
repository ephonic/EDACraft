module leaf(input var logic a,output logic b);assign b=a;endmodule module top;logic a=0;wire b;leaf dut(a,b);initial begin #1;a=1;#1;$display("TRACE var %b",b);end endmodule
