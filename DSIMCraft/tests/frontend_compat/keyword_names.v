module keyword_tb;
  integer ref, const, logic, new, unique, enum, return;
  initial begin
    ref=1;const=2;logic=3;new=4;unique=5;enum=6;return=7;
    if(ref+const+logic+new+unique+enum+return!=28) $fatal(1,"Verilog names");
    $display("TRACE keywords %0d",ref+const+logic+new+unique+enum+return);
    $finish;
  end
endmodule
