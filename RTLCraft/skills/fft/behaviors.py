"""
skills.fft.behaviors — Framework compatibility shim.
"""
from skills.fft.functional import *
from skills.fft.cycle_level import *

# arch_templates compat aliases (functional-level)
fft_delay_buffer_template = fftdelaybuffer_functional
fft_controller_template = fftcontroller_functional
fft_multiply_template = fftmultiply_functional
fft_sdf_unit2_template = fftsdfunit2_functional
fft_sdf_unit_template = fftsdfunit_functional
fft_twiddle_template = ffttwiddle_functional
