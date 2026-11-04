module top;
 mailbox dynamic_box=new;
 mailbox #(int) signed_box=new;
 mailbox #(byte) byte_box=new;
 bit signed[31:0] packed_value=7;
 bit signed[7:0] packed_byte=-3;
 int value,bad;byte byte_value;
 initial begin
  dynamic_box.put(packed_value);dynamic_box.get(value);if(value!=7)bad++;
  signed_box.put(13);signed_box.get(packed_value);if(packed_value!=13)bad++;
  byte_box.put(packed_byte);byte_box.get(byte_value);if(byte_value!=-3)bad++;
  $display("TRACE equivalence %0d %0d %0d %0d",value,packed_value,byte_value,bad);$finish;
 end
endmodule
