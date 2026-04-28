# physical-design — Placement, Routing & Signoff

## Overview

Backend design automation: floorplanning, standard-cell placement, global/detailed routing, DFT insertion, and physical signoff (DRC, LVS, STA).

## Status

🚧 **Reserved directory** — Reference flows will be added in future releases.

## Planned Contents

| Item | Description |
|------|-------------|
| `floorplan_generator.py` | Automatic floorplan from hierarchy and area estimates |
| `placement_demo.py` | Placement-aware RTL transformations |
| `route_estimator.py` | Wirelength and congestion estimation from netlist |

## Existing Integration

rtlgen already includes basic placement support:

```python
from rtlgen.placement import place_design
```

## See Also

- `../synthesis/SKILL.md` — Logic synthesis and timing analysis
