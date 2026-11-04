// Generated from owned AST/IR; functional qualification is separate.
module dut (
  input wire clk,
  input wire rst_n,
  input wire in_valid,
  input wire in_ready,
  input wire in_wen,
  input wire in_mode,
  input wire [3:0] in_a,
  input wire [3:0] in_b,
  input wire [3:0] in_c,
  input wire [3:0] in_d,
  input wire [3:0] in_addr,
  input wire [31:0] in_data,
  input wire [12:0] in_tag,
  output wire out_ready,
  output reg out_valid,
  output reg [31:0] out_value,
  output reg [12:0] out_tag
);
  reg [31:0] words[0:15];
  reg [31:0] history;
  reg [0:0] _agent_ms_busy;
  reg [2:0] _agent_ms_index;
  reg [0:0] _agent_ms_write_enable;
  reg [3:0] _agent_ms_write_address;
  reg [31:0] _agent_ms_old_word;
  reg [31:0] _agent_ms_snap_0;
  reg [3:0] _agent_ms_snap_1;
  reg [3:0] _agent_ms_snap_2;
  reg [3:0] _agent_ms_snap_3;
  reg [3:0] _agent_ms_snap_4;
  reg [3:0] _agent_ms_snap_5;
  reg [31:0] _agent_ms_snap_6;
  reg [0:0] _agent_ms_snap_7;
  reg [0:0] _agent_ms_snap_8;
  reg [12:0] _agent_ms_snap_9;
  reg [0:0] _agent_ms_snap_10;
  reg [0:0] _agent_ms_snap_11;
  reg [12:0] _agent_ms_snap_12;
  reg [0:0] _agent_ms_snap_13;
  reg [31:0] _agent_ms_snap_14;
  reg [3:0] _agent_ms_address_0;
  reg [3:0] _agent_ms_address_1;
  reg [3:0] _agent_ms_address_2;
  reg [3:0] _agent_ms_address_3;
  reg [31:0] _agent_ms_read_0;
  reg [31:0] _agent_ms_read_1;
  reg [31:0] _agent_ms_read_2;
  reg [31:0] _agent_ms_read_3;
  wire [3:0] _agent_ms_port_address;
  assign _agent_ms_port_address = (_agent_ms_busy ? ((_agent_ms_index == 3'd0) ? _agent_ms_address_0 : ((_agent_ms_index == 3'd1) ? _agent_ms_address_1 : ((_agent_ms_index == 3'd2) ? _agent_ms_address_2 : _agent_ms_address_3))) : in_addr);
  wire [31:0] _agent_ms_raw_word;
  assign _agent_ms_raw_word = words[_agent_ms_port_address];
  wire [31:0] _agent_ms_read_value;
  assign _agent_ms_read_value = ((_agent_ms_write_enable && (_agent_ms_port_address == _agent_ms_write_address)) ? _agent_ms_old_word : _agent_ms_raw_word);
  assign out_ready = (rst_n && ((!_agent_ms_busy) && ((!out_valid) || in_ready)));
  always @(posedge clk or negedge rst_n)
    if ((!rst_n))
      begin
        out_valid <= 1'b0;
        out_value <= 32'd0;
        out_tag <= 13'd7;
        history <= 32'd3;
        _agent_ms_busy <= 1'd0;
        _agent_ms_index <= 3'd0;
        _agent_ms_write_enable <= 1'd0;
        _agent_ms_write_address <= 4'd0;
        _agent_ms_old_word <= 32'd0;
        _agent_ms_snap_0 <= 32'd0;
        _agent_ms_snap_1 <= 4'd0;
        _agent_ms_snap_2 <= 4'd0;
        _agent_ms_snap_3 <= 4'd0;
        _agent_ms_snap_4 <= 4'd0;
        _agent_ms_snap_5 <= 4'd0;
        _agent_ms_snap_6 <= 32'd0;
        _agent_ms_snap_7 <= 1'd0;
        _agent_ms_snap_8 <= 1'd0;
        _agent_ms_snap_9 <= 13'd0;
        _agent_ms_snap_10 <= 1'd0;
        _agent_ms_snap_11 <= 1'd0;
        _agent_ms_snap_12 <= 13'd0;
        _agent_ms_snap_13 <= 1'd0;
        _agent_ms_snap_14 <= 32'd0;
        _agent_ms_address_0 <= 4'd0;
        _agent_ms_address_1 <= 4'd0;
        _agent_ms_address_2 <= 4'd0;
        _agent_ms_address_3 <= 4'd0;
        _agent_ms_read_0 <= 32'd0;
        _agent_ms_read_1 <= 32'd0;
        _agent_ms_read_2 <= 32'd0;
        _agent_ms_read_3 <= 32'd0;
      end
    else
      begin
        if ((out_valid && in_ready))
          out_valid <= 1'd0;
        if ((out_ready && in_valid))
          begin
            _agent_ms_busy <= 1'd1;
            _agent_ms_index <= 3'd0;
            _agent_ms_write_enable <= (1'b1 && (((rst_n && 1'((rst_n && ((!out_valid) || in_ready)))) && in_valid) && in_wen));
            _agent_ms_write_address <= in_addr;
            if ((1'b1 && (((rst_n && 1'((rst_n && ((!out_valid) || in_ready)))) && in_valid) && in_wen)))
              _agent_ms_old_word <= _agent_ms_raw_word;
            _agent_ms_snap_0 <= history;
            _agent_ms_snap_1 <= in_a;
            _agent_ms_snap_2 <= in_addr;
            _agent_ms_snap_3 <= in_b;
            _agent_ms_snap_4 <= in_c;
            _agent_ms_snap_5 <= in_d;
            _agent_ms_snap_6 <= in_data;
            _agent_ms_snap_7 <= in_mode;
            _agent_ms_snap_8 <= in_ready;
            _agent_ms_snap_9 <= in_tag;
            _agent_ms_snap_10 <= in_valid;
            _agent_ms_snap_11 <= in_wen;
            _agent_ms_snap_12 <= out_tag;
            _agent_ms_snap_13 <= out_valid;
            _agent_ms_snap_14 <= out_value;
            _agent_ms_address_0 <= in_a;
            _agent_ms_address_1 <= in_b;
            _agent_ms_address_2 <= in_c;
            _agent_ms_address_3 <= in_d;
          end
        else
          if (_agent_ms_busy)
            if ((_agent_ms_index < 3'd4))
              begin
                if ((_agent_ms_index == 3'd0))
                  _agent_ms_read_0 <= _agent_ms_read_value;
                if ((_agent_ms_index == 3'd1))
                  _agent_ms_read_1 <= _agent_ms_read_value;
                if ((_agent_ms_index == 3'd2))
                  _agent_ms_read_2 <= _agent_ms_read_value;
                if ((_agent_ms_index == 3'd3))
                  _agent_ms_read_3 <= _agent_ms_read_value;
                _agent_ms_index <= (_agent_ms_index + 3'd1);
              end
            else
              begin
                begin
                  if (_agent_ms_snap_7)
                    out_value <= (32'(_agent_ms_read_0) ^ 32'(_agent_ms_read_1));
                  else
                    out_value <= (32'(_agent_ms_read_0) - 32'(_agent_ms_read_1));
                  history <= (_agent_ms_read_2 + _agent_ms_snap_0);
                  if (_agent_ms_snap_11)
                    out_value <= (_agent_ms_snap_14 + _agent_ms_read_3);
                  out_tag <= _agent_ms_snap_9;
                end
                _agent_ms_busy <= 1'd0;
                out_valid <= 1'd1;
              end
      end
  always @(posedge clk)
    if (((out_ready && in_valid) && (1'b1 && (((rst_n && 1'((rst_n && ((!out_valid) || in_ready)))) && in_valid) && in_wen))))
      words[in_addr] <= in_data;
endmodule

