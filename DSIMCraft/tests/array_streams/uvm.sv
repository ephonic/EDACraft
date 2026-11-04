// Minimal reproduction of the next unmodified full-UVM blocker; pending support.
module top;
  typedef bit bit_q_t[$];
  byte bytes[$];
  bit bits[$];
  int observed;
  initial begin
    bytes = '{8'hc7,8'h3f};
    bits = {<<8{bit_q_t'({<<{bytes}})}};
    foreach(bits[i]) observed=(observed<<1)|bits[i];
    $display("TRACE dynamic_stream %0d %04h",bits.size(),observed);
  end
endmodule
