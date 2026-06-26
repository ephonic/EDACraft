"""
skills.noc.models — NoC Behavioral Models

Mesh Network-on-Chip behavioral models:
  - FlitState: Per-flit tracking (type, header, payload)
  - RouterState: Per-router state (buffer occupancy, FSM, stats)
  - RouterModel: Single 5-port router behavioral model
  - NoCModel: Full mesh network behavioral model
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Flit type encoding
FLIT_HEAD = 0b00
FLIT_BODY = 0b01
FLIT_TAIL = 0b10
FLIT_SINGLE = 0b11

# Port mapping
PORT_E = 0
PORT_W = 1
PORT_N = 2
PORT_S = 3
PORT_INJ = 4

PORT_NAMES = ["E", "W", "N", "S", "INJ"]


# =====================================================================
# Flit State
# =====================================================================

@dataclass
class FlitState:
    """Per-flit tracking."""
    flit_type: int = FLIT_SINGLE
    dest_x: int = 0
    dest_y: int = 0
    src_x: int = 0
    src_y: int = 0
    flit_id: int = 0
    payload: int = 0

    @staticmethod
    def from_bits(bits: int) -> "FlitState":
        flit = FlitState()
        flit.flit_type = (bits >> 62) & 0x3
        flit.dest_y = (bits >> 9) & 0x7
        flit.dest_x = (bits >> 6) & 0x7
        flit.src_y = (bits >> 3) & 0x7
        flit.src_x = bits & 0x7
        flit.flit_id = (bits >> 12) & 0x3FFFFFFFFFFFF
        flit.payload = bits & 0xFFFFFFFFFFF
        return flit

    def to_bits(self) -> int:
        header = ((self.dest_y & 0x7) << 9) | ((self.dest_x & 0x7) << 6) | \
                 ((self.src_y & 0x7) << 3) | (self.src_x & 0x7)
        return (self.flit_type << 62) | (self.flit_id << 12) | header


# =====================================================================
# Router State
# =====================================================================

@dataclass
class RouterState:
    """Per-router state tracking."""
    x: int = 0
    y: int = 0
    # Per-port buffer
    buffer_count: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    buffer_depth: int = 4
    # Per-port FSM state
    fsm_state: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    # Flits in flight
    flits_received: int = 0
    flits_forwarded: int = 0
    flits_ejected: int = 0
    # Packets
    packets_injected: int = 0
    packets_received: int = 0

    def empty_slots(self, port: int) -> int:
        return self.buffer_depth - self.buffer_count[port]

    def push_flit(self, port: int) -> bool:
        if self.buffer_count[port] < self.buffer_depth:
            self.buffer_count[port] += 1
            return True
        return False

    def pop_flit(self, port: int) -> bool:
        if self.buffer_count[port] > 0:
            self.buffer_count[port] -= 1
            return True
        return False


# =====================================================================
# Router Model
# =====================================================================

class RouterModel:
    """Single 5-port router behavioral model.

    Models the router pipeline:
    Buffer Write → Route Compute → VC Alloc → Switch Traversal → Crossbar → Output
    """

    def __init__(
        self,
        x: int = 0,
        y: int = 0,
        mesh_size: int = 8,
        buffer_depth: int = 4,
        num_ports: int = 5,
        name: str = "Router",
    ):
        self.name = name
        self.x = x
        self.y = y
        self.mesh_size = mesh_size
        self.buffer_depth = buffer_depth
        self.num_ports = num_ports

        self.state = RouterState(x=x, y=y, buffer_depth=buffer_depth)
        self.cycle_count = 0
        self._running = False

        # Pending flits per input port
        self._pending_flits: Dict[int, List[FlitState]] = {p: [] for p in range(num_ports)}

        # Crossbar select (default: no connection)
        self._crossbar_sel = [7, 7, 7, 7, 7]  # s_e, s_w, s_n, s_s, s_eject

    def _xy_route(self, x_cur: int, y_cur: int, x_dest: int, y_dest: int) -> int:
        """XY routing: return output port bitmask."""
        if x_cur < x_dest:
            return 1 << PORT_E
        elif x_cur > x_dest:
            return 1 << PORT_W
        else:
            if y_cur < y_dest:
                return 1 << PORT_N
            elif y_cur > y_dest:
                return 1 << PORT_S
            else:
                return 1 << PORT_INJ  # Eject (arrived)

    def inject_flit(self, flit: FlitState) -> bool:
        """Inject a flit into the injection port."""
        if self.state.push_flit(PORT_INJ):
            self._pending_flits[PORT_INJ].append(flit)
            self.state.flits_received += 1
            return True
        return False

    def step(self) -> Dict[str, Any]:
        """Advance one cycle. Returns per-port stats."""
        self.cycle_count += 1
        stats = {"forwarded": 0, "ejected": 0, "injected": 0}

        # Process each input port
        for port in range(self.num_ports):
            if not self._pending_flits[port]:
                continue

            flit = self._pending_flits[port][0]
            out_port_mask = self._xy_route(self.x, self.y, flit.dest_x, flit.dest_y)

            # Find target output port
            target = -1
            for p in range(self.num_ports):
                if out_port_mask & (1 << p):
                    target = p
                    break

            if target < 0:
                self._pending_flits[port].pop(0)
                self.state.pop_flit(port)
                continue

            if target == PORT_INJ:
                # Arrived at destination — eject
                self._pending_flits[port].pop(0)
                self.state.pop_flit(port)
                self.state.flits_ejected += 1
                stats["ejected"] += 1
                if flit.flit_type in (FLIT_TAIL, FLIT_SINGLE):
                    self.state.packets_received += 1
            else:
                # Forward to next router (simplified: assume always succeeds)
                self._pending_flits[port].pop(0)
                self.state.pop_flit(port)
                self.state.flits_forwarded += 1
                stats["forwarded"] += 1

        return stats

    def run(self, num_cycles: int = 1000) -> Dict[str, Any]:
        """Run behavioral simulation."""
        for _ in range(num_cycles):
            self.step()

        return {
            "cycles": self.cycle_count,
            "flits_received": self.state.flits_received,
            "flits_forwarded": self.state.flits_forwarded,
            "flits_ejected": self.state.flits_ejected,
            "packets_received": self.state.packets_received,
            "buffer_usage": list(self.state.buffer_count),
        }


# =====================================================================
# NoC Model (Full Mesh Network)
# =====================================================================

class NoCModel:
    """Mesh Network-on-Chip behavioral model.

    Models an M×M grid of routers with east/west/north/south links.
    Each node has a packet generator and receiver.
    """

    def __init__(
        self,
        mesh_size: int = 8,
        buffer_depth: int = 4,
        flit_width: int = 64,
        name: str = "NoC",
    ):
        self.name = name
        self.mesh_size = mesh_size
        self.buffer_depth = buffer_depth
        self.flit_width = flit_width
        self.total_nodes = mesh_size * mesh_size

        self.routers: List[RouterModel] = []
        for y in range(mesh_size):
            for x in range(mesh_size):
                r = RouterModel(
                    x=x, y=y, mesh_size=mesh_size,
                    buffer_depth=buffer_depth, name=f"Router_{x}_{y}",
                )
                self.routers.append(r)

        self.cycle_count = 0
        self.total_injected = 0
        self.total_received = 0
        self._packet_queue: Dict[Tuple[int, int], List[FlitState]] = {}
        self._injection_ptr = 0  # Round-robin injection pointer

    def _get_router(self, x: int, y: int) -> Optional[RouterModel]:
        if 0 <= x < self.mesh_size and 0 <= y < self.mesh_size:
            return self.routers[y * self.mesh_size + x]
        return None

    def _generate_flit(self, src_x: int, src_y: int, pkt_cnt: int, flit_type: int) -> FlitState:
        """Generate a flit with deterministic pseudo-random destination."""
        dest_x = (src_x + 1 + pkt_cnt) % self.mesh_size
        dest_y = (src_y + 1 + pkt_cnt // self.mesh_size) % self.mesh_size
        if dest_x == src_x and dest_y == src_y:
            dest_x = (dest_x + 1) % self.mesh_size
        node_id = src_y * self.mesh_size + src_x
        return FlitState(
            flit_type=flit_type,
            dest_x=dest_x, dest_y=dest_y,
            src_x=src_x, src_y=src_y,
            flit_id=(pkt_cnt << 6) | node_id,
        )

    def _forward_flit(self, from_x: int, from_y: int, flit: FlitState, out_port: int):
        """Forward flit to next router based on output port."""
        nx, ny = from_x, from_y
        if out_port == PORT_E:
            nx = from_x + 1
        elif out_port == PORT_W:
            nx = from_x - 1
        elif out_port == PORT_N:
            ny = from_y + 1
        elif out_port == PORT_S:
            ny = from_y - 1
        elif out_port == PORT_INJ:
            return  # Eject — handled by router

        target = self._get_router(nx, ny)
        if target and target.state.push_flit(PORT_INJ):
            target._pending_flits[PORT_INJ].append(flit)
            target.state.flits_received += 1

    def step(self) -> Dict[str, Any]:
        """Advance one cycle for the entire network."""
        self.cycle_count += 1

        # Inject new packets (round-robin, 1 packet per cycle)
        node_idx = self._injection_ptr % self.total_nodes
        src_x = node_idx % self.mesh_size
        src_y = node_idx // self.mesh_size
        router = self._get_router(src_x, src_y)
        if router and router.state.empty_slots(PORT_INJ) > 0:
            pkt_cnt = self.total_injected
            # Single-flit packet (HEAD=SINGLE)
            flit = self._generate_flit(src_x, src_y, pkt_cnt, FLIT_SINGLE)
            if router.inject_flit(flit):
                self.total_injected += 1

        self._injection_ptr += 1

        # Step all routers
        for router in self.routers:
            stats = router.step()
            self.total_received += stats["ejected"]

        return {
            "cycle": self.cycle_count,
            "injected": self.total_injected,
            "received": self.total_received,
        }

    def run(self, num_cycles: int = 5000) -> Dict[str, Any]:
        """Run behavioral simulation for num_cycles."""
        for _ in range(num_cycles):
            self.step()

        total_flits = sum(r.state.flits_received for r in self.routers)
        total_ejected = sum(r.state.flits_ejected for r in self.routers)

        return {
            "cycles": self.cycle_count,
            "packets_injected": self.total_injected,
            "packets_received": self.total_received,
            "total_flits_routed": total_flits,
            "total_flits_ejected": total_ejected,
            "avg_latency": self.cycle_count // max(1, self.total_received),
            "injection_rate": self.total_injected / max(1, self.cycle_count),
            "completion_rate": self.total_received / max(1, self.total_injected),
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "mesh_size": f"{self.mesh_size}x{self.mesh_size}",
            "total_nodes": self.total_nodes,
            "cycles": self.cycle_count,
            "injected": self.total_injected,
            "received": self.total_received,
            "flits_in_flight": sum(
                sum(len(pf) for pf in r._pending_flits.values())
                for r in self.routers
            ),
        }
