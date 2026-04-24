"""
Signal edge item for rendering connections between module ports.
"""

from PyQt6.QtWidgets import QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont


class SignalEdgeItem(QGraphicsPathItem):
    """
    QGraphicsPathItem representing a signal connection between two ports.

    Draws a cubic Bezier curve between source and destination ports and
    renders a signal name label at the midpoint. Colors vary by signal width
    or signal type.
    """

    def __init__(self, signal, src_node, dst_node, parent=None):
        """
        Initialize a signal edge.

        Args:
            signal: VizSignal instance.
            src_node: ModuleNodeItem for the source module.
            dst_node: ModuleNodeItem for the destination module.
            parent: Optional parent QGraphicsItem.
        """
        super().__init__(parent)
        self.signal = signal
        self.src_node = src_node
        self.dst_node = dst_node

        self.src_node.add_edge(self)
        self.dst_node.add_edge(self)

        self.setZValue(-1)
        self.setPen(QPen(self._choose_color(), 2, Qt.PenStyle.SolidLine))

        self._font = QFont("Segoe UI", 8)
        self.update_path()

    def _choose_color(self):
        """Select edge color based on signal width or type."""
        width = getattr(self.signal, 'width', 1)
        sig_type = getattr(self.signal, 'signal_type', 'wire')

        if sig_type == 'clock':
            return QColor("#D32F2F")   # red
        if sig_type == 'reset':
            return QColor("#7B1FA2")   # purple
        if width >= 64:
            return QColor("#E64A19")   # deep orange
        if width >= 32:
            return QColor("#FBC02D")   # amber
        if width >= 16:
            return QColor("#388E3C")   # green
        if width >= 8:
            return QColor("#1976D2")   # blue
        return QColor("#757575")       # grey

    def update_path(self):
        """Recompute the Bezier path based on current port positions."""
        src_port = getattr(self.signal, 'src_port', '')
        dst_port = getattr(self.signal, 'dst_port', '')
        src_pos = self.src_node.get_port_scene_pos(src_port)
        dst_pos = self.dst_node.get_port_scene_pos(dst_port)

        if src_pos is None or dst_pos is None:
            self.setPath(QPainterPath())
            return

        path = QPainterPath()
        path.moveTo(src_pos)

        # Control points for cubic bezier
        dx = abs(dst_pos.x() - src_pos.x())
        offset = max(dx * 0.5, 50)
        ctrl1 = QPointF(src_pos.x() + offset, src_pos.y())
        ctrl2 = QPointF(dst_pos.x() - offset, dst_pos.y())
        path.cubicTo(ctrl1, ctrl2, dst_pos)

        self.setPath(path)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """Paint the edge path and signal label."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        super().paint(painter, option, widget)

        # Draw label at midpoint
        path = self.path()
        if path.isEmpty():
            return

        mid = path.pointAtPercent(0.5)
        name = getattr(self.signal, 'name', '')
        if not name:
            return

        painter.setFont(self._font)
        painter.setPen(QPen(QColor("#212121")))

        metrics = painter.fontMetrics()
        text_rect = metrics.boundingRect(name)
        text_rect.moveCenter(mid.toPoint())
        text_rect.adjust(-2, -1, 2, 1)

        painter.fillRect(text_rect, QColor(255, 255, 255, 220))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, name)
