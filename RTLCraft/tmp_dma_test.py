import sys
sys.path.insert(0, 'g:/code/rtlgen/rtlgen')

from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.core import NeuralAccel

params = NeuralAccelParams(array_size=32, data_width=16, acc_width=32, sram_depth=65536, num_lanes=32)
npu = NeuralAccel(params=params)

print(f"dma.words_per_beat = {npu.dma.words_per_beat}")
print(f"dma.data_width = {npu.dma.data_width}")
print(f"dma.axi_data_width = {npu.dma.axi_data_width}")
