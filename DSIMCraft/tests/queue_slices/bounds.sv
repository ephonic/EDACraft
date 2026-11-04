module top;
  int q[$], stage=0;
  task automatic show(input string label, input int values[$]);
    $write("TRACE %s",label);
    foreach(values[i]) $write(" %0d",values[i]);
    $display(" size=%0d",values.size());
  endtask
  task automatic take(input int first, input int last);
    show($sformatf("%0d:%0d",first,last),q[first:last]);
    stage++; #1;
  endtask
  initial begin
    q='{10,20,30,40,50};
    take(1,3); take(-2,2); take(2,100); take(100,200);
    take(3,1); take(0,-1); take(-5,-2); take(0,0);
    take('x,2); take(0,'x);
    show("tail",q[$-1:$]); stage++; #1;
    show("reverse",q[$:0]); stage++; #1;
    show("wide",q[128'h100000000:128'h100000002]); stage++; #1;
    show("huge",q[128'h100000000000000000000:128'h100000000000000000002]); stage++; #1;
    q=q[1:$-1]; show("self",q); stage++; #1;
    q=q[0:-1]; show("cleared",q); stage++; #1;
    show("empty",q[0:$]); $finish;
  end
endmodule
