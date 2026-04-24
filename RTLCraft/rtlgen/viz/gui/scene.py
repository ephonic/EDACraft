"""
Interactive graphics scene for hardware module visualization.
"""

from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush


class VizScene(QGraphicsScene):
    """
    QGraphicsScene subclass that manages module nodes and signal edges.

    Provides a background grid, zoom via mouse wheel, and pan via middle-click drag.
    """

    GRID_SIZE = 20
    GRID_COLOR = QColor("#E0E0E0")

    def __init__(self, parent=None):
        """
        Initialize the visualization scene.

        Args:
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._nodes = {}   # instance_name -> ModuleNodeItem
        self._edges = []   # list of SignalEdgeItem
        self._panning = False
        self._pan_start = None

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw a light grid pattern over the background."""
        super().drawBackground(painter, rect)

        left = int(rect.left()) - (int(rect.left()) % self.GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % self.GRID_SIZE)

        pen = QPen(self.GRID_COLOR)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        # Draw vertical lines
        x = left
        while x < rect.right():
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += self.GRID_SIZE

        # Draw horizontal lines
        y = top
        while y < rect.bottom():
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += self.GRID_SIZE

    def add_node(self, node):
        """
        Add a module node to the scene.

        Args:
            node: ModuleNodeItem instance.
        """
        inst_name = getattr(node.module, 'instance_name', None)
        if inst_name:
            self._nodes[inst_name] = node
        self.addItem(node)

    def add_edge(self, edge):
        """
        Add a signal edge to the scene.

        Args:
            edge: SignalEdgeItem instance.
        """
        self._edges.append(edge)
        self.addItem(edge)

    def remove_node(self, node):
        """Remove a node and all attached edges from the scene."""
        inst_name = getattr(node.module, 'instance_name', None)
        if inst_name and inst_name in self._nodes:
            del self._nodes[inst_name]

        edges_to_remove = [e for e in self._edges if e.src_node == node or e.dst_node == node]
        for edge in edges_to_remove:
            self.remove_edge(edge)

        self.removeItem(node)

    def remove_edge(self, edge):
        """Remove a signal edge from the scene."""
        if edge in self._edges:
            self._edges.remove(edge)
        if edge.src_node:
            edge.src_node.remove_edge(edge)
        if edge.dst_node:
            edge.dst_node.remove_edge(edge)
        self.removeItem(edge)

    def clear_scene(self):
        """Remove all nodes and edges from the scene."""
        self._nodes.clear()
        self._edges.clear()
        self.clear()

    def get_node(self, instance_name):
        """
        Retrieve a node by its instance name.

        Args:
            instance_name: The instance name of the module.

        Returns:
            ModuleNodeItem or None.
        """
        return self._nodes.get(instance_name)

    def mousePressEvent(self, event):
        """Handle mouse press; middle button initiates pan."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.scenePos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move; middle button drag pans the view."""
        if self._panning:
            delta = event.scenePos() - self._pan_start
            self._pan_start = event.scenePos()
            for view in self.views():
                hbar = view.horizontalScrollBar()
                vbar = view.verticalScrollBar()
                if hbar is not None:
                    hbar.setValue(int(hbar.value() - delta.x()))
                if vbar is not None:
                    vbar.setValue(int(vbar.value() - delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release; end pan on middle button release."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Zoom in/out on mouse wheel."""
        # QGraphicsSceneWheelEvent may not have angleDelta (PyQt6)
        if hasattr(event, 'angleDelta'):
            delta = event.angleDelta().y()
        elif hasattr(event, 'delta'):
            delta = event.delta()
        else:
            delta = 120
        factor = 1.15 if delta > 0 else 1 / 1.15
        for view in self.views():
            view.scale(factor, factor)
        event.accept()
