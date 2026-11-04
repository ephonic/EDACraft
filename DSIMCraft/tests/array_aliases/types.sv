module top;
 typedef enum logic[2:0] {RED=1,BLUE=4} Color;
 typedef Color CQ[$];
 typedef logic[128:0] Wide;
 typedef Wide DA[];
 typedef bit[128:0] Two;
 typedef Two DB[];
 CQ colors;DA data;DB converted;
 logic[128:0] observed;
 function automatic CQ make(input Color c);return {c,BLUE};endfunction
 function automatic CQ implicit_result();implicit_result={RED};implicit_result.push_back(BLUE);endfunction
 function automatic DA words(input Wide value);
  DA local_words;local_words=new[2];local_words[0]=value;local_words[1]='1;return local_words;
 endfunction
 initial begin
  colors=make(RED);$display("TRACE enum %s %s",colors[0].name(),colors[1].name());
  colors=implicit_result();data=words(129'hx1);converted=data;
  $display("TRACE typed %0d %s %h %h",colors.size(),colors[1].name(),data[0],converted[0]);
  observed=data[0];#1;$finish;
 end
endmodule
