"""cam Layer 2: Template registry."""
from rtlgen.registry import TemplateRegistry
from skills.mem.cam.functional import *

TemplateRegistry.register('priority_encoder', priority_encoder_template)
TemplateRegistry.register('ram_dp', ram_dp_template)
TemplateRegistry.register('cam_srl', cam_srl_template)
TemplateRegistry.register('cam_bram', cam_bram_template)
TemplateRegistry.register('cam_top', cam_top_template)
