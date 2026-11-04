module top;
 logic signed [128:0] wide_values[$];logic [128:0] unsigned_values[$];
 string words[$];int observed;
 initial begin
  wide_values='{129'sh10000000000000000000000001,-129'sd5,129'sd0,129'sh20000000000000000000000001};
  wide_values.sort;if(wide_values[0]!=-129'sd5||wide_values[3]!=129'sh20000000000000000000000001)$fatal(1,"wide signed");
  wide_values.rsort with(item);if(wide_values[3]!=-129'sd5)$fatal(1,"wide rsort");
  unsigned_values='{129'h100000000000000000000000000,129'd1,129'h20000000000000000000000000};
  unsigned_values.sort();if(unsigned_values[0]!=1||unsigned_values[2]!=129'h100000000000000000000000000)$fatal(1,"wide unsigned");
  words='{"z","alpha","a","middle","aa",""};words.sort;
  if(words[0]!=""||words[1]!="a"||words[2]!="aa"||words[5]!="z")$fatal(1,"lexical strings");
  words.rsort();if(words[0]!="z"||words[5]!="")$fatal(1,"reverse strings");
  words.sort(s) with(s.len());if(words[0].len()!=0||words[5].len()!=6)$fatal(1,"string numeric key");
  words.reverse();observed=words[0].len();$display("TRACE ordering keys %0d",observed);$finish;
 end
endmodule
