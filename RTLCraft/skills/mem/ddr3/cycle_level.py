"""ddr3 Layer 2: Template registry."""
from rtlgen.registry import TemplateRegistry
from skills.mem.ddr3.functional import *

TemplateRegistry.register('memory_controller', memory_controller_template)
TemplateRegistry.register('dfi_sequencer', dfi_sequencer_template)
