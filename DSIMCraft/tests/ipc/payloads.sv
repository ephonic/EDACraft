`timescale 1ps/1ps
module top;
 typedef enum logic[1:0] {IDLE=0,BUSY=2} state_t;
 class Item;int value;endclass
 class Channel;
  mailbox #(int) box=new;
  task send(input int v);box.put(v);endtask
  task receive(ref int v);box.get(v);endtask
 endclass
 mailbox #(longint) longs=new;
 mailbox #(logic[127:0]) wide_box=new;
 mailbox #(state_t) states=new;
 mailbox #(int) slot=new(1),alias_slot;
 Channel channel=new;
 Item original,changed,target;
 state_t state=IDLE;
 logic[127:0] wide_value;
 longint signed_value;
 int source=51,calls,value,bad;
 function automatic int message();calls++;return source;endfunction
 initial begin
  longs.put(-7);longs.get(signed_value);if(signed_value!=-7)bad++;
  wide_box.put(128'hfedcba98765432100123456789abcdef);wide_box.get(wide_value);
  if(wide_value!==128'hfedcba98765432100123456789abcdef)bad++;
  states.put(BUSY);states.get(state);if(state!=BUSY)bad++;
  original=new;changed=new;target=original;
  fork
   channel.box.get(target.value);
   begin #1;target=changed;channel.send(73);end
  join
  if(original.value!=73||changed.value!=0)bad++;
  fork
   channel.receive(value);
   begin #1;channel.send(77);end
  join
  if(value!=77)bad++;
  slot.put(10);alias_slot=slot;
  fork
   begin slot.put(message());end
   begin #1;source=99;slot=new;alias_slot.get(value);end
  join
  alias_slot.get(value);if(value!=51||calls!=1||slot.num()!=0)bad++;
  $display("TRACE payloads %0d %0d %0d %0d",signed_value,original.value,value,bad);$finish;
 end
endmodule
