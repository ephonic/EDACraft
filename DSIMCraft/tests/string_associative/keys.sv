module top;
  logic [128:0] words[string];
  int keys[string];
  string key;int ok,count,calls;logic [128:0] observed,missing;
  function string next_key();calls=calls+1;if(calls==1)return "k0";return "k1";endfunction
  initial begin
    keys[""]=1;keys["a"]=2;keys["ab"]=3;keys["z"]=4;keys["\200"]=5;keys["\377"]=6;
    keys[32'h61]=12;keys[0]=11;
    ok=keys.first(key);
    while(ok)begin count=count+1;$display("TRACE key %0d %0d %0d",key.len(),key.getc(0),keys[key]);ok=keys.next(key);end
    $display("TRACE exhausted %0d %0d %0d",ok,key.len(),count);
    ok=keys.last(key);$display("TRACE last %0d %0d",ok,key.getc(0));
    key="abx";ok=keys.prev(key);$display("TRACE prev %0d %s",ok,key);
    key="aa";ok=keys.next(key);$display("TRACE next %0d %s",ok,key);
    words[next_key()]=129'h1fedcba987654321001122334455667788;
    words[next_key()]=129'h0123456789abcdef0aabbccddeeff0011;
    words["k0"][7:0]=8'bz10x0110;observed=words["k0"];missing=words["absent"];
    $display("TRACE wide %b %b",observed,missing);
    $display("TRACE state %0d %0d %0d %0d",calls,words.size(),words.exists("absent"),keys.num());
    keys.delete();ok=keys.first(key);$display("TRACE empty %0d %0d %0d",ok,key.len(),keys.num());
    $finish;
  end
endmodule
