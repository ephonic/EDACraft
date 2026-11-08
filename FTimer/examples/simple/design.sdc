create_clock -period 10.0 -name clk -waveform {0 5} [get_ports in1]
set_input_transition 0.05 [get_ports in1]
