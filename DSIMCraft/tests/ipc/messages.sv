module top;
 class Item;int value;endclass
 typedef mailbox #(string) string_box;
 mailbox dynamic_box=new;
 string_box texts=new;
 mailbox #(Item) objects=new;
 mailbox #(real) reals=new;
 Item original,received;
 string text="abc",copy="old";
 int number=17,got=99,bad;
 bit[7:0] selected;bit[31:0] raw;
 real fraction=1.25,result;
 initial begin
  dynamic_box.put(number);dynamic_box.put(text);dynamic_box.put(fraction);
  if(dynamic_box.try_get(copy)!=-1||copy!="old"||dynamic_box.num()!=3)bad++;
  dynamic_box.get(got);dynamic_box.peek(copy);
  if(got!=17||copy!="abc"||dynamic_box.num()!=2)bad++;
  dynamic_box.get(copy);dynamic_box.get(result);if(result!=1.25)bad++;
  dynamic_box.put(number[7:0]);dynamic_box.get(selected);if(selected!=17)bad++;
  dynamic_box.put(number[31:0]);if(dynamic_box.try_get(got)!=-1||got!=17)bad++;
  dynamic_box.get(raw);if(raw!=17)bad++;
  texts.put("hello");texts.get(copy);if(copy!="hello")bad++;
  original=new;original.value=31;objects.put(original);objects.get(received);
  received.value=37;if(original.value!=37)bad++;
  reals.put(2.5);reals.get(result);if(result!=2.5)bad++;
  $display("TRACE messages %0d %s %0d %0d",got,copy,original.value,bad);
  $finish;
 end
endmodule
