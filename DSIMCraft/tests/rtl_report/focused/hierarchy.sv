module leaf;logic[7:0] hidden=7;endmodule module top;leaf dut();initial $display("TRACE hierarchy %h",dut.hidden);endmodule
