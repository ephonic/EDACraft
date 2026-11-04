module top;
  byte character;
  logic [71:0] word;
  logic [8:0] partial;
  string result, identity;
  int calls;
  function automatic byte next_character();calls++;return 8'h41;endfunction
  initial begin
    character=8'h3a;
    result={"prefix",string'(character),"suffix"};
    if(result!="prefix:suffix")$fatal(1,"integral cast in string concatenation");
    word=72'h410042004300440045;
    result=string'(word);if(result!="ABCDE")$fatal(1,"wide cast and removed zero bytes");
    partial=9'h142;result=string'(partial);
    if(result.len()!=2 || result.getc(0)!=1 || result.getc(1)!=8'h42)$fatal(1,"partial byte padding");
    result=string'(8'b010x0001);if(result!="A")$fatal(1,"two-state character conversion");
    result=string'(8'hff);if(result.len()!=1 || result.getc(0)!=-1)$fatal(1,"byte sign");
    identity="hello";result=string'(identity);if(result!=identity)$fatal(1,"string identity");
    result=string'(next_character());if(result!="A" || calls!=1)$fatal(1,"single evaluation");
    if(string'(16'h4142)!="AB" || $bits(string'(16'h4142))!=16)$fatal(1,"constant operand cast");
    if($bits(string'(32'b0))!=0)$fatal(1,"empty cast");
    identity=1'bx ? string'(16'h4142) : string'(16'h4142);
    if(identity!="AB")$fatal(1,"equivalent ambiguous string branches");
    identity=1'bx ? string'(16'h4142) : string'(16'h4344);
    if(identity!="")$fatal(1,"different ambiguous string branches");
    $display("TRACE string casts value=%s calls=%0d",result,calls);$finish;
  end
endmodule
