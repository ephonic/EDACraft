"""Entry point: python -m rtlgen.viz --target <module_path>"""

import sys
import argparse
import importlib

from PyQt6.QtWidgets import QApplication

from rtlgen.viz.scanner import scan_module
from rtlgen.viz.layout import auto_layout
from rtlgen.viz.gui.main_window import VizMainWindow


def main():
    parser = argparse.ArgumentParser(description="RTLGen Hardware Architecture Visualizer")
    parser.add_argument(
        "--target",
        required=True,
        help="Python import path to the rtlgen Module class (e.g. skills.cpu.npu.core.NeuralAccel)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1400,
        help="Canvas width (default: 1400)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=900,
        help="Canvas height (default: 900)",
    )
    args = parser.parse_args()

    # Dynamically import the target module class
    parts = args.target.split(".")
    module_path = ".".join(parts[:-1])
    class_name = parts[-1]

    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error importing {module_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if not hasattr(mod, class_name):
        print(f"Error: {args.target} does not have class '{class_name}'", file=sys.stderr)
        sys.exit(1)

    TargetClass = getattr(mod, class_name)

    try:
        instance = TargetClass()
    except Exception as e:
        print(f"Error instantiating {args.target}: {e}", file=sys.stderr)
        sys.exit(1)

    # Scan and layout
    graph = scan_module(instance)
    auto_layout(graph, width=args.width, height=args.height)

    # Launch GUI
    app = QApplication(sys.argv)
    window = VizMainWindow(graph)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
