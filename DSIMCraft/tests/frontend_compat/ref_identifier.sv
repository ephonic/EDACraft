module top;
  integer ref;
  initial begin
    ref = 7;
    if (ref != 7) $fatal(1, "ref identifier");
    $display("TRACE identifier ref=%0d", ref);
    $finish;
  end
endmodule
