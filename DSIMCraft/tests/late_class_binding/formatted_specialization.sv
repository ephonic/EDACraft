virtual class Utility #(type T=int);
 static int calls=7;
 static function string text(input T value); calls++; return $sformatf("%0h/%0d",value,calls); endfunction
endclass
class Recorder;
 function void write(input logic[127:0] value,input int fd);
  $fdisplay(fd,"%s",Utility#(logic[127:0])::text(value));
 endfunction
endclass
module top;
 Recorder r;int fd;
 initial begin r=new();fd=$fopen("values.txt","w");r.write(128'hab,fd);r.write(128'hcd,fd);$fclose(fd);$display("TRACE done");$finish;end
endmodule
