`timescale 1ps/1ps
module leaf;
  reg [15:0] word;
  reg [15:0] mem[1:3];
  reg [0:1][0:7] packed_word;
  wire [15:0] observed = mem[2] ^ word;
endmodule
module top;
  leaf u(), v();
  integer i, lane;
  task automatic flip(ref reg [15:0] value);
    value = value ^ 16'h00ff;
  endtask
  initial begin
    u.word=16'h1234; v.word=16'habcd;
    u.mem[1]=16'h1001; u.mem[2]=16'h2002; u.mem[3]=16'h3003;
    v.mem[1]=16'h4004; v.mem[2]=16'h5005; v.mem[3]=16'h6006;
    u.packed_word=16'h1234;
    i=1;u.mem[i++][3:0]=4'hc;
    lane=1;u.word[lane++*4+:4]+=4'h3;
    {u.mem[2][7:0],v.word[3:0]}=12'h5ae;
    u.packed_word[0][0+:4]=4'ha;
    flip(v.mem[3]);
    #1;
    if(i!=2||lane!=2||u.mem[1]!=16'h100c||u.word!=16'h1264||u.mem[2]!=16'h205a||v.word!=16'habce||v.mem[3]!=16'h60f9||u.packed_word!=16'ha234)
      $fatal(1,"blocking hierarchy writes failed");
    if(u.observed!=(16'h205a^16'h1264))$fatal(1,"hierarchical write did not wake reader");
    i=1;u.mem[i++][7:0]<=#2 8'he7;
    u.word[7:4]<=#2 4'hf;
    if(i!=2)$fatal(1,"NBA index side effect");
    i=3;
    #1;if(u.mem[1]!=16'h100c||u.word!=16'h1264)$fatal(1,"NBA too early");
    #2;if(u.mem[1]!=16'h10e7||u.mem[3]!=16'h3003||u.word!=16'h12f4)$fatal(1,"NBA hierarchy target");
    if(v.mem[1]!=16'h4004||v.mem[2]!=16'h5005)$fatal(1,"instance storage alias");
    $display("TRACE hierarchy basic %h %h %h %h",u.word,u.mem[1],v.word,u.packed_word);
    $finish;
  end
endmodule
