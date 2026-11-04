module top;byte q[$]='{8'h12,8'h34};int value;initial begin value=int'({>>{q}});$display("TRACE packed_cast %h",value);end endmodule
