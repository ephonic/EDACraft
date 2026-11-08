"""Synthetic units/propagation example; no foundry library is required."""
from pathlib import Path
from ftimer import FTimer, SwitchingActivity

root=Path(__file__).resolve().parent
timer=FTimer(liberty=root/'cells.lib',verilog=root/'top.v',sdc=root/'top.sdc')
detail=timer.estimate_power_detail(1e9,0,activities={
    'a':SwitchingActivity(2e8,.2),'b':SwitchingActivity(3e8,.5)})
print(detail.summary)
print('coverage:',detail.coverage)
for net in detail.nets:
    if net['name'] in ('d','q','y'):
        print(net['name'],net['toggle_rate_hz'],'Hz',net['probability'])
for cell in detail.cells:
    if cell['name']=='unused_output':
        print('Open output: internal =',cell['internal_w'],'W; switching =',cell['switching_w'],'W')
