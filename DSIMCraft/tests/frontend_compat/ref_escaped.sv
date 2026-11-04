module top;
  integer \ref ;
  function integer \new ;
    input integer n;
    begin \new = n+2;end
  endfunction
  initial begin
    \ref = \new (5);
    if (\ref != 7) $fatal(1, "escaped identifier");
    $display("TRACE escaped ref=%0d", \ref );
    $finish;
  end
endmodule
