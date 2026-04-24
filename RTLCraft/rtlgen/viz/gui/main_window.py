"""Main window for rtlgen visualizer."""

import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGraphicsView, QDockWidget, QTreeWidget, QTreeWidgetItem,
    QToolBar, QStatusBar, QFileDialog, QMessageBox, QLabel,
    QPushButton, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QAction, QKeySequence, QPainter, QImage, QPainter

from rtlgen.viz.model import VizGraph, VizModule
from rtlgen.viz.gui.scene import VizScene
from rtlgen.viz.gui.node_item import ModuleNodeItem
from rtlgen.viz.gui.edge_item import SignalEdgeItem


class VizMainWindow(QMainWindow):
    """Main window with canvas, property panel, and toolbar."""

    def __init__(self, graph: Optional[VizGraph] = None):
        super().__init__()
        self._graph: Optional[VizGraph] = None
        self._scene = VizScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHints(QPainter.RenderHint.Antialiasing)
        self._view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self._view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        self._setup_ui()
        self._setup_toolbar()
        self._setup_menubar()
        self._setup_property_panel()
        self._setup_statusbar()

        if graph is not None:
            self.load_graph(graph)

        # Connect selection changed to property panel update
        self._scene.selectionChanged.connect(self._on_selection_changed)

    def _setup_ui(self):
        self.setWindowTitle("RTLGen Visualizer")
        self.setGeometry(100, 100, 1400, 900)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Canvas area
        self._view.setMinimumWidth(800)
        splitter.addWidget(self._view)

        # Property panel (will be added as dock, but placeholder here)
        self._prop_widget = QWidget()
        self._prop_layout = QVBoxLayout(self._prop_widget)
        self._prop_tree = QTreeWidget()
        self._prop_tree.setHeaderLabels(["Property", "Value"])
        self._prop_tree.setColumnWidth(0, 150)
        self._prop_layout.addWidget(QLabel("<b>Module Properties</b>"))
        self._prop_layout.addWidget(self._prop_tree)
        splitter.addWidget(self._prop_widget)
        splitter.setSizes([1100, 300])

    def _setup_toolbar(self):
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        act_zoom_in = QAction("Zoom In", self)
        act_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        act_zoom_in.triggered.connect(self._zoom_in)
        toolbar.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom Out", self)
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(self._zoom_out)
        toolbar.addAction(act_zoom_out)

        act_fit = QAction("Fit All", self)
        act_fit.setShortcut(QKeySequence("Ctrl+0"))
        act_fit.triggered.connect(self.fit_all)
        toolbar.addAction(act_fit)

        toolbar.addSeparator()

        act_export = QAction("Export PNG", self)
        act_export.triggered.connect(self._export_png)
        toolbar.addAction(act_export)

    def _setup_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        view_menu = menubar.addMenu("&View")

        act_zoom_in = QAction("Zoom &In", self)
        act_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        act_zoom_in.triggered.connect(self._zoom_in)
        view_menu.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom &Out", self)
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(self._zoom_out)
        view_menu.addAction(act_zoom_out)

        act_fit = QAction("&Fit All", self)
        act_fit.setShortcut(QKeySequence("Ctrl+0"))
        act_fit.triggered.connect(self.fit_all)
        view_menu.addAction(act_fit)

    def _setup_property_panel(self):
        self._prop_tree.clear()
        self._prop_tree.setColumnCount(2)
        self._prop_tree.setHeaderLabels(["Property", "Value"])

    def _setup_statusbar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    def load_graph(self, graph: VizGraph):
        """Load a VizGraph into the canvas."""
        self._graph = graph
        self._scene.clear()
        self._scene._nodes.clear()
        self._scene._edges.clear()

        # Create node items
        for mod in graph.modules:
            node = ModuleNodeItem(mod)
            node.setPos(mod.x, mod.y)
            self._scene.addItem(node)
            self._scene._nodes[mod.instance_name] = node

        # Create edge items (simplified: just show edges that connect known nodes)
        for sig in graph.signals:
            src_node = self._scene._nodes.get(sig.src_module)
            dst_node = self._scene._nodes.get(sig.dst_module)
            if src_node and dst_node:
                edge = SignalEdgeItem(sig, src_node, dst_node)
                self._scene.addItem(edge)
                self._scene._edges.append(edge)

        self.setWindowTitle(f"RTLGen Visualizer — {graph.name}")
        self._status.showMessage(f"Loaded {len(graph.modules)} modules, {len(graph.signals)} signals")

        # Select first module to populate property panel
        if graph.modules:
            first = list(self._scene._nodes.values())[0]
            first.setSelected(True)
            self._on_selection_changed()

    def clear_scene(self):
        """Clear the canvas."""
        self._scene.clear()
        self._scene._nodes.clear()
        self._scene._edges.clear()
        self._prop_tree.clear()

    def fit_all(self):
        """Zoom to fit all items."""
        self._view.fitInView(self._scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _zoom_in(self):
        self._view.scale(1.2, 1.2)

    def _zoom_out(self):
        self._view.scale(1 / 1.2, 1 / 1.2)

    def _export_png(self):
        """Export current view to PNG."""
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "rtlgen_viz.png", "PNG (*.png)")
        if not path:
            return

        # Render scene to image
        rect = self._scene.itemsBoundingRect()
        img = QImage(int(rect.width()) + 100, int(rect.height()) + 100, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.white)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._scene.render(painter, target=QRectF(0, 0, img.width(), img.height()), source=rect)
        painter.end()

        if img.save(path):
            self._status.showMessage(f"Exported to {path}")
        else:
            QMessageBox.warning(self, "Export Failed", f"Could not save image to {path}")

    def _on_selection_changed(self):
        """Update property panel when selection changes."""
        selected = [item for item in self._scene.selectedItems() if isinstance(item, ModuleNodeItem)]
        self._prop_tree.clear()

        if not selected:
            self._prop_tree.addTopLevelItem(QTreeWidgetItem(["No selection", ""]))
            return

        node = selected[0]
        mod = node.module

        # Module info
        self._prop_tree.addTopLevelItem(QTreeWidgetItem(["Module Type", mod.name]))
        self._prop_tree.addTopLevelItem(QTreeWidgetItem(["Instance Name", mod.instance_name]))

        # Ports
        ports_item = QTreeWidgetItem(["Ports", f"{len(mod.ports)}"])
        for port in mod.ports:
            ports_item.addChild(QTreeWidgetItem([
                f"  {port.name}",
                f"{port.direction} [{port.width-1}:0]"
            ]))
        self._prop_tree.addTopLevelItem(ports_item)
        ports_item.setExpanded(True)

        # Parameters
        if mod.params:
            params_item = QTreeWidgetItem(["Parameters", f"{len(mod.params)}"])
            for k, v in mod.params.items():
                params_item.addChild(QTreeWidgetItem([f"  {k}", str(v)]))
            self._prop_tree.addTopLevelItem(params_item)
            params_item.setExpanded(True)

        # Connected signals count
        self._prop_tree.addTopLevelItem(QTreeWidgetItem([
            "Connections", f"{len(node._edges)}"
        ]))

        self._prop_tree.resizeColumnToContents(0)
