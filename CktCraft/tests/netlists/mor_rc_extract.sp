* MOR test: extract RC parasitic network from C1_1.spi, drive with pulse
* 验证：原始 RC 网络 vs amor 降阶后 RC 网络的瞬态响应一致性
* pulse from 0 to 5V, measure delay to node O69
vin1 in1 0 PULSE(0 5 5n 0.1n 0.1n 25n 50n)
* 以下是从 C1_1.spi 提取的 RC 网络（仅含 R/C 器件，MOSFET 已移除）
* --- RC parasites start ---
RC1 in1 3010 10
RC2 in1 3038 10
RC3 in1 3066 10
RC4 in1 3094 10
RC5 in1 3122 10
CC1 3010 0 1e-15
CC2 3038 0 1e-15
CC3 3066 0 1e-15
CC4 3094 0 1e-15
CC5 3122 0 1e-15
RC6 3010 3182 5
RC7 3038 3210 5
RC8 3066 3238 5
RC9 3094 3266 5
RC10 3122 3294 5
CC6 3182 0 1e-15
CC7 3210 0 1e-15
CC8 3238 0 1e-15
CC9 3266 0 1e-15
CC10 3294 0 1e-15
RC11 3182 4953 20
CC11 4953 0 2e-15
* O69 = node 4953
.tran 0.1n 200n
.print v(in1) v(4953)
.end
