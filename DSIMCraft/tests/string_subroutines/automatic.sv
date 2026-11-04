`timescale 1ns/1ps
module top;
  string first,second;
  int done=0;
  task automatic delayed(input string value,input int delay_ns,output string answer);
    string saved;
    if(saved!=""||answer!="")$fatal(1,"automatic string initialization");
    saved={value,"/saved"};
    #2;
    answer=#(delay_ns) {saved,"/done"};
    if(answer!={value,"/saved/done"})$fatal(1,"overlapping automatic string frames");
  endtask
  initial begin #1;delayed("one",3,first);done++;end
  initial begin #2;delayed("two",1,second);done++;end
  initial begin
    #8;
    if(done!=2||first!="one/saved/done"||second!="two/saved/done")$fatal(1,"delayed string output");
    $display("TRACE automatic [%s] [%s] %0d",first,second,done);
    $finish;
  end
endmodule
