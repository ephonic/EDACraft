module top;
  int fd, result, matched, a, b, c, stage=0;
  function automatic int emit_values(input int file_handle,input int value);
    $fdisplay(file_handle,"%0d %0d",value,value+1);
    $fwrite(file_handle,"%0d\n",value+2);
    $display("TRACE emit %0d",value);
    $write("TRACE write %0d\n",value+3);
    return value+4;
  endfunction
  initial begin
    fd=$fopen("values.txt","w");
    result=emit_values(fd,7); $fclose(fd); stage++; #1;
    fd=$fopen("values.txt","r"); matched=$fscanf(fd,"%d %d %d",a,b,c); $fclose(fd);
    $display("TRACE file %0d %0d %0d %0d result=%0d",matched,a,b,c,result);
    stage++; #1; $finish;
  end
endmodule
