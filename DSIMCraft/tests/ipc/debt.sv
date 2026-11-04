// IEEE 1800-2023 15.3.1 permits negative initial key counts.
module top;
 semaphore keys=new(-2);
 int first,second,third;
 initial begin
  first=keys.try_get();keys.put(3);second=keys.try_get();third=keys.try_get();
  $display("TRACE debt %0d %0d %0d",first,second,third);$finish;
 end
endmodule
