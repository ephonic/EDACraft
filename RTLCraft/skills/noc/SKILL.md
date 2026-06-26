# NoC (Network-on-Chip) Skill

Mesh-based Network-on-Chip design for Spec2RTL flow.

## Architecture

```
Network (8x8 mesh)
  └── Process_Node × 64
        └── Router (5-port)
              ├── InputUnit × 5 (East, West, North, South, Inject)
              │     ├── Buffer (4-depth FIFO)
              │     └── Route_Func (XY routing)
              ├── OutputUnit × 5 (East, West, North, South, Eject)
              ├── VC_Alloc (round-robin VC allocation)
              ├── Select_gen (crossbar select decoding)
              ├── set_Alloc (output port allocation)
              ├── ST_Controler (switch traversal control)
              ├── ST (switch traversal enable generation)
              ├── out_en_gen (output enable flags)
              └── CrossBar (5×5 switch fabric)
```

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| FLIT_WIDTH | 64 | Flit data width |
| X_WIDTH / Y_WIDTH | 3 | Coordinate bit-width |
| MESH_SIZE | 8 | 8×8 mesh topology |
| BUFFER_DEPTH | 4 | Per-input-port buffer depth |
| NUM_PORTS | 5 | Ports per router (E/W/N/S/Inject) |
| NUM_VC | 1 | Virtual channels per port |

## Port Mapping

| Index | Direction | Signal Prefix |
|-------|-----------|---------------|
| 0 | East | e_ / OE |
| 1 | West | w_ / OW |
| 2 | North | n_ / ON |
| 3 | South | s_ / OS |
| 4 | Inject/Eject | inject_ / Eject |

## Flit Header Format (64-bit)

| Bits | Field | Description |
|------|-------|-------------|
| [63:62] | flit_type | 00=HEAD, 01=BODY, 10=TAIL, 11=SINGLE |
| [61:12] | Flit_ID | {packet_count[45:0], node_id[5:0]} |
| [11:9] | dest_Y | Destination Y coordinate |
| [8:6] | dest_X | Destination X coordinate |
| [5:3] | src_Y | Source Y coordinate |
| [2:0] | src_X | Source X coordinate |

## Pipeline Stages (per router)

1. **Buffer Write** — flit arrives, pushed into input buffer
2. **Route Computation** — XY routing determines valid output ports
3. **VC Allocation** — round-robin arbitration for output port access
4. **Switch Traversal** — crossbar select signal generation
5. **Crossbar Traversal** — flit routed through 5×5 crossbar
6. **Output Write** — flit written to next router's input buffer

## InputUnit FSM (7 states)

| State | Action |
|-------|--------|
| 0 | Idle: wait for vc_grant |
| 1 | Wait for ST_ack |
| 2-5 | Switch traversal (push flit to crossbar) |
| 6 | Cleanup: release VC |

## Quick Start

```python
from skills.noc.behaviors import router_template, input_unit_template
from skills.noc.models import RouterModel, NoCModel
from skills.noc.skeleton_templates import register_noc_skeleton_steps

# Register skeleton steps
from rtlgen import arch_skel
register_noc_skeleton_steps(arch_skel._TEMPLATE_STEPS)

# Behavioral simulation
router = RouterModel(x=0, y=0, mesh_size=8)
router.run(num_cycles=1000)

noc = NoCModel(mesh_size=8, flit_width=64)
result = noc.run(num_cycles=5000)
print(f"Packets injected: {result['packets_injected']}")
print(f"Packets received: {result['packets_received']}")
```

## Pipeline Stages

| PE Type | Description | Key Logic |
|---------|-------------|-----------|
| router | 5-port router top-level | InputUnit × 5, OutputUnit × 5, CrossBar, VC_Alloc |
| input_unit | Input processing unit | Buffer, Route_Func, 7-state FSM |
| output_unit | Output buffer unit | Write request generation |
| vc_alloc | Virtual channel allocator | 5 round-robin counters |
| crossbar | 5×5 switch fabric | Multiplexer-based routing |
| route_func | XY routing function | Coordinate comparison |
| buffer | 4-depth FIFO | Push/pop with empty_slots |
| packet_gen | Traffic generator | HEAD/BODY/TAIL flit sequence |
| packet_rec | Packet receiver | Flit collection and reassembly |
| st_controler | Switch traversal control | ST request/ack handshake |
| select_gen | Crossbar select decoder | Grant-based select signal |
| set_alloc | Output port allocator | VC grant → output port mapping |
| out_en_gen | Output enable generation | Push signal → enable flags |
