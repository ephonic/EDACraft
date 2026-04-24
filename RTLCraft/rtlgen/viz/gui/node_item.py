"""
Module node item for interactive hardware module visualization.
"""

from collections import defaultdict
from typing import List, Dict, Any

from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QFontMetricsF


class _PortGroup:
    """A single port or a grouped bus port for display."""
    def __init__(self, name: str, direction: str, width: int, ports: List[Any]):
        self.name = name
        self.direction = direction
        self.width = width
        self.ports = ports  # original VizPort objects
        self.is_bus = len(ports) > 1


def _group_ports(ports: List[Any]) -> List[_PortGroup]:
    """Group vector ports like weight_in_0..weight_in_31 into bus ports."""
    groups: Dict[str, List[Any]] = defaultdict(list)
    singles: List[Any] = []

    for p in ports:
        name = getattr(p, 'name', '')
        if '_' in name:
            prefix, suffix = name.rsplit('_', 1)
            if suffix.isdigit():
                groups[prefix].append(p)
                continue
        singles.append(p)

    result: List[_PortGroup] = []

    for p in singles:
        result.append(_PortGroup(
            name=p.name,
            direction=getattr(p, 'direction', 'input'),
            width=getattr(p, 'width', 1),
            ports=[p],
        ))

    for prefix, members in sorted(groups.items(), key=lambda x: x[0]):
        indices = sorted(int(p.name.rsplit('_', 1)[1]) for p in members)
        if len(indices) >= 2 and indices == list(range(min(indices), max(indices) + 1)):
            direction = getattr(members[0], 'direction', 'input')
            width = getattr(members[0], 'width', 1)
            result.append(_PortGroup(
                name=f"{prefix}[{max(indices)}:{min(indices)}]",
                direction=direction,
                width=width,
                ports=members,
            ))
        else:
            for p in members:
                result.append(_PortGroup(
                    name=p.name,
                    direction=getattr(p, 'direction', 'input'),
                    width=getattr(p, 'width', 1),
                    ports=[p],
                ))

    return result


class ModuleNodeItem(QGraphicsItem):
    """
    QGraphicsItem representing a hardware module instance.

    Renders a rounded rectangle with the module name at the top,
    input ports as small circles on the left edge, and output ports
    as small circles on the right edge. Supports selection and dragging.
    Vector ports (e.g. weight_in_0..weight_in_31) are grouped into
    a single bus port to save space.
    """

    MIN_WIDTH = 120
    MIN_HEIGHT = 80
    HEADER_HEIGHT = 24
    PORT_DIAMETER = 10
    PORT_MARGIN = 6
    CORNER_RADIUS = 8
    TEXT_MARGIN = 6

    FILL_COLOR = QColor("#E3F2FD")
    BORDER_COLOR = QColor("#1976D2")
    SELECTED_BORDER_COLOR = QColor("#FF5722")
    PORT_COLOR = QColor("#424242")
    BUS_PORT_COLOR = QColor("#1565C0")
    TEXT_COLOR = QColor("#212121")

    def __init__(self, module, parent=None):
        """
        Initialize a module node.

        Args:
            module: VizModule instance containing name, instance_name, ports, etc.
            parent: Optional parent QGraphicsItem.
        """
        super().__init__(parent)
        self.module = module
        self._edges = []  # SignalEdgeItem instances attached to this node

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self._font = QFont("Segoe UI", 9)
        self._header_font = QFont("Segoe UI", 10)
        self._header_font.setBold(True)
        self._fm = QFontMetricsF(self._font)
        self._header_fm = QFontMetricsF(self._header_font)

        raw_ports = list(getattr(module, 'ports', []))
        raw_inputs = [p for p in raw_ports if getattr(p, 'direction', 'input') == 'input']
        raw_outputs = [p for p in raw_ports if getattr(p, 'direction', 'input') != 'input']

        self._input_groups = _group_ports(raw_inputs)
        self._output_groups = _group_ports(raw_outputs)

        self.setToolTip(self._build_tooltip())

        # Mapping from original port name -> group name for edge lookup
        self._port_to_group: Dict[str, str] = {}
        for g in self._input_groups + self._output_groups:
            for p in g.ports:
                self._port_to_group[getattr(p, 'name', '')] = g.name

        self._port_positions: Dict[str, QPointF] = {}  # port_name -> local coords
        self._compute_geometry()

    def _build_tooltip(self):
        """Build the tooltip string for this node."""
        name = getattr(self.module, 'name', 'Unknown')
        inst = getattr(self.module, 'instance_name', 'Unknown')
        n_ports = len(getattr(self.module, 'ports', []))
        in_groups = getattr(self, '_input_groups', [])
        out_groups = getattr(self, '_output_groups', [])
        n_buses = sum(1 for g in in_groups + out_groups if g.is_bus)
        return f"Module: {name}\nInstance: {inst}\nPorts: {n_ports} ({n_buses} buses)"

    def _compute_geometry(self):
        """Compute the bounding rect and port positions based on content."""
        inst_name = getattr(self.module, 'instance_name', 'Unknown')
        module_name = getattr(self.module, 'name', '')
        header_text = f"{inst_name} ({module_name})" if module_name else inst_name
        text_width = self._header_fm.horizontalAdvance(header_text) + 2 * self.TEXT_MARGIN

        max_ports = max(len(self._input_groups), len(self._output_groups), 1)
        port_height = self.PORT_DIAMETER + self.PORT_MARGIN
        port_block_height = max_ports * port_height + self.PORT_MARGIN
        height = max(self.MIN_HEIGHT, self.HEADER_HEIGHT + port_block_height)

        # Ensure width accommodates ports on both sides with internal padding
        width = max(self.MIN_WIDTH, text_width + 2 * self.PORT_DIAMETER + 20)

        self._width = width
        self._height = height

        # Compute port positions
        self._port_positions.clear()

        # Input ports on left
        y_start = self.HEADER_HEIGHT + self.PORT_MARGIN + self.PORT_DIAMETER / 2
        for i, group in enumerate(self._input_groups):
            y = y_start + i * port_height
            pos = QPointF(self.PORT_DIAMETER / 2, y)
            self._port_positions[group.name] = pos
            # Also map each original port to this position
            for p in group.ports:
                self._port_positions[getattr(p, 'name', '')] = pos

        # Output ports on right
        for i, group in enumerate(self._output_groups):
            y = y_start + i * port_height
            pos = QPointF(self._width - self.PORT_DIAMETER / 2, y)
            self._port_positions[group.name] = pos
            for p in group.ports:
                self._port_positions[getattr(p, 'name', '')] = pos

    def boundingRect(self):
        """Return the bounding rectangle in local coordinates."""
        pen_width = 2.0
        return QRectF(
            -pen_width / 2,
            -pen_width / 2,
            self._width + pen_width,
            self._height + pen_width
        )

    def shape(self):
        """Return the item shape for hit detection."""
        path = QPainterPath()
        path.addRoundedRect(
            0, 0, self._width, self._height,
            self.CORNER_RADIUS, self.CORNER_RADIUS
        )
        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """Paint the module node with header, body, ports, and selection highlight."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self._width, self._height)

        # Fill
        painter.setBrush(self.FILL_COLOR)
        pen = QPen(self.BORDER_COLOR, 2)
        if self.isSelected():
            pen.setColor(self.SELECTED_BORDER_COLOR)
            pen.setWidth(3)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

        # Header separator
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.drawLine(
            QPointF(0, self.HEADER_HEIGHT),
            QPointF(self._width, self.HEADER_HEIGHT)
        )

        # Header text (instance name + module name)
        painter.setFont(self._header_font)
        painter.setPen(QPen(self.TEXT_COLOR))
        inst_name = getattr(self.module, 'instance_name', 'Unknown')
        module_name = getattr(self.module, 'name', '')
        header_text = inst_name if not module_name else f"{inst_name} ({module_name})"
        header_rect = QRectF(
            self.TEXT_MARGIN, 2,
            self._width - 2 * self.TEXT_MARGIN,
            self.HEADER_HEIGHT - 4
        )
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignCenter, header_text)

        # Ports
        painter.setFont(self._font)
        for group in self._input_groups + self._output_groups:
            pos = self._port_positions.get(group.name)
            if pos is None:
                continue

            is_input = group.direction == 'input'
            is_bus = group.is_bus

            # Draw port circle
            r = self.PORT_DIAMETER / 2
            painter.setBrush(QColor("#FFFFFF"))
            painter.setPen(QPen(self.BUS_PORT_COLOR if is_bus else self.PORT_COLOR, 1.5 if is_bus else 1))
            painter.drawEllipse(pos, r, r)

            # Draw port name
            painter.setPen(QPen(self.TEXT_COLOR))
            text_rect = QRectF(
                self.PORT_DIAMETER + 2 if is_input else self._width - self.PORT_DIAMETER - 2 - 100,
                pos.y() - self._fm.height() / 2,
                100,
                self._fm.height()
            )
            align = (
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                if is_input else
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            painter.drawText(text_rect, align, group.name)

    def itemChange(self, change, value):
        """
        Notify attached edges when position has changed so they can update their paths.
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_path()
        return super().itemChange(change, value)

    def add_edge(self, edge):
        """Register an edge that is connected to this node."""
        if edge not in self._edges:
            self._edges.append(edge)

    def remove_edge(self, edge):
        """Unregister an edge from this node."""
        if edge in self._edges:
            self._edges.remove(edge)

    def get_port_scene_pos(self, port_name):
        """
        Return the scene coordinates of the named port.

        Args:
            port_name: Name of the port (original or group name).

        Returns:
            QPointF in scene coordinates, or None if port not found.
        """
        local_pos = self._port_positions.get(port_name)
        if local_pos is None:
            return None
        return self.mapToScene(local_pos)

    def hoverMoveEvent(self, event):
        """Update tooltip to show the port under the cursor."""
        pos = event.pos()
        tooltip = self._build_tooltip()
        for group in self._input_groups + self._output_groups:
            port_pos = self._port_positions.get(group.name)
            if port_pos is None:
                continue
            # Check distance to port center
            dx = pos.x() - port_pos.x()
            dy = pos.y() - port_pos.y()
            if dx * dx + dy * dy <= (self.PORT_DIAMETER / 2 + 2) ** 2:
                if group.is_bus:
                    tooltip = f"Bus: {group.name}\nDirection: {group.direction}\nWidth: {group.width}\nMembers: {len(group.ports)}"
                else:
                    p = group.ports[0]
                    width = getattr(p, 'width', 1)
                    direction = getattr(p, 'direction', '')
                    port_type = getattr(p, 'port_type', 'wire')
                    tooltip = f"Port: {group.name}\nDirection: {direction}\nWidth: {width}\nType: {port_type}"
                break
        self.setToolTip(tooltip)
        super().hoverMoveEvent(event)

    def hoverEnterEvent(self, event):
        """Change cursor on hover."""
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Restore cursor and tooltip on leave."""
        self.unsetCursor()
        self.setToolTip(self._build_tooltip())
        super().hoverLeaveEvent(event)
