"""Schematic editing tools for analog circuit design.

Provides high-level operations for creating and modifying schematic views.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import EDATool, ToolProgress, ToolResult


class SchematicEditTool(EDATool):
    """Create or edit schematic elements: instances, wires, nets, pins, shapes."""

    name = "schematic_edit"
    aliases = ["sch_edit", "edit_schematic"]
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_inst", "create_wire", "create_net", "create_pin", "create_text", "create_shape", "delete"],
                "description": "The schematic editing action to perform.",
            },
            "params": {
                "type": "object",
                "description": "Action-specific parameters.",
            },
        },
        "required": ["action", "params"],
    }
    requires_design_open = True

    def description(self) -> str:
        return (
            "Edit the schematic view of the active design. Actions include: "
            "create_inst (place component instance), create_wire (draw wire), "
            "create_net (create named net), create_pin (add pin), "
            "create_text (add label), create_shape (rectangle, ellipse, etc.), delete."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        try:
            import pyAether
        except ImportError:
            return ToolResult(data={"error": "pyAether is not available."})

        design = getattr(context, "active_design", None)
        block = getattr(context, "active_block", None)
        namespace = getattr(context, "namespace", None)

        if design is None or block is None:
            return ToolResult(data={"error": "No active schematic design. Use design_open first."})

        action = args["action"]
        params = args.get("params", {})

        try:
            if action == "create_inst":
                return await self._create_inst(pyAether, namespace, block, params)
            elif action == "create_wire":
                return await self._create_wire(pyAether, block, params)
            elif action == "create_net":
                return await self._create_net(pyAether, namespace, block, params)
            elif action == "create_pin":
                return await self._create_pin(pyAether, namespace, block, params)
            elif action == "create_text":
                return await self._create_text(pyAether, block, params)
            elif action == "create_shape":
                return await self._create_shape(pyAether, block, params)
            elif action == "delete":
                return await self._delete(pyAether, block, params)
            else:
                return ToolResult(data={"error": f"Unknown action: {action}"})
        except Exception as e:
            return ToolResult(data={"error": str(e)})

    async def _create_inst(self, pyAether: Any, namespace: Any, block: Any, params: Dict[str, Any]) -> ToolResult:
        master_lib = params["master_lib"]
        master_cell = params["master_cell"]
        master_view = params.get("master_view", "symbol")
        inst_name = params["inst_name"]
        point = tuple(params["point"])
        orient = params.get("orient", "R0")
        inst_params = params.get("inst_params", None)

        lib_scl = pyAether.emyScalarName(namespace, master_lib)
        cell_scl = pyAether.emyScalarName(namespace, master_cell)
        view_scl = pyAether.emyScalarName(namespace, master_view)

        reserved_view = pyAether.emyReservedViewType("schematicSymbol")
        view_type = pyAether.emyViewType.get(reserved_view)

        master = pyAether.emyDesign.open(lib_scl, cell_scl, view_scl, view_type, "r")

        inst_scl_name = pyAether.emyScalarName(namespace, inst_name)
        pnt_x, pnt_y = point
        trans = pyAether.emyTransform((pnt_x, pnt_y), getattr(pyAether, f"emc{orient}", pyAether.emcR0))

        pyAether.emyScalarInst.create(
            block, master, inst_scl_name, trans,
            inst_params,
            pyAether.emyBlockDomainVisibility(pyAether.emcInheritFromTopBlock),
            pyAether.emyPlacementStatus(pyAether.emcNonePlacementStatus),
        )

        return ToolResult(data={"action": "create_inst", "inst_name": inst_name, "point": point})

    async def _create_wire(self, pyAether: Any, block: Any, params: Dict[str, Any]) -> ToolResult:
        start_point = tuple(params["start_point"])
        end_point = tuple(params["end_point"])
        layer_num = params.get("layer_num", 0)  # Default schematic wire layer
        purpose_num = params.get("purpose_num", 0)

        points = [start_point, end_point]
        wire = pyAether.emyLine.create(block, layer_num, purpose_num, points)

        return ToolResult(data={"action": "create_wire", "wire": str(wire)})

    async def _create_net(self, pyAether: Any, namespace: Any, block: Any, params: Dict[str, Any]) -> ToolResult:
        net_name = params["net_name"]
        wires = params.get("wires", [])
        ellipses = params.get("ellipses", [])
        sig_type = params.get("sig_type", "signal")
        is_global = params.get("is_global", False)

        sig_type_enum = pyAether.emySigType(getattr(pyAether, f"emc{sig_type.capitalize()}SigType", pyAether.emcSignalSigType))
        net = pyAether.emyScalarName(namespace, net_name)
        scl_net = pyAether.emyScalarNet.create(block, net, sig_type_enum, is_global,
                                                  pyAether.emyBlockDomainVisibility(pyAether.emcInheritFromTopBlock))

        # Attach wires to net (would need wire object references in real impl)
        return ToolResult(data={"action": "create_net", "net_name": net_name})

    async def _create_pin(self, pyAether: Any, namespace: Any, block: Any, params: Dict[str, Any]) -> ToolResult:
        net_name = params["net_name"]
        pin_name = params["pin_name"]
        point = tuple(params["point"])
        term_type = params.get("term_type", "input")
        master_lib = params.get("master_lib", "basic")
        master_cell = params.get("master_cell", "ipin")

        # Find or create net
        # Simplified: would need to look up existing net
        sig_type = pyAether.emySigType(pyAether.emcSignalSigType)
        net = pyAether.emyScalarName(namespace, net_name)
        scl_net = pyAether.emyScalarNet.create(block, net, sig_type, False,
                                                  pyAether.emyBlockDomainVisibility(pyAether.emcInheritFromTopBlock))

        term_name = pyAether.emyName(namespace, pin_name)
        term_type_enum = getattr(pyAether, f"emc{term_type.capitalize()}TermType", pyAether.emcInputTermType)
        term = pyAether.emyTerm.create(scl_net, term_name, pyAether.emyTermType(term_type_enum))

        return ToolResult(data={"action": "create_pin", "pin_name": pin_name})

    async def _create_text(self, pyAether: Any, block: Any, params: Dict[str, Any]) -> ToolResult:
        text = params["text"]
        origin = tuple(params["origin"])
        layer_num = params.get("layer_num", 0)
        purpose_num = params.get("purpose_num", 0)
        height = params.get("height", 13)
        alignment = params.get("alignment", "CenterLeft")
        orient = params.get("orient", "R0")
        font = params.get("font", "Stick")

        align_enum = getattr(pyAether, f"emc{alignment}TextAlign", pyAether.emcCenterLeftTextAlign)
        orient_enum = getattr(pyAether, f"emc{orient}", pyAether.emcR0)
        font_enum = getattr(pyAether, f"emc{font}Font", pyAether.emcStickFont)

        pyAether.emyText.create(
            block, layer_num, purpose_num, text, origin,
            pyAether.emyTextAlign(align_enum),
            pyAether.emyOrient(orient_enum),
            pyAether.emyFont(font_enum),
            height,
        )
        return ToolResult(data={"action": "create_text", "text": text})

    async def _create_shape(self, pyAether: Any, block: Any, params: Dict[str, Any]) -> ToolResult:
        shape_type = params["shape_type"]
        bbox = tuple(params.get("bbox", []))
        layer_num = params.get("layer_num", 0)
        purpose_num = params.get("purpose_num", 0)

        if shape_type == "rect":
            pyAether.emyRect.create(block, layer_num, purpose_num, bbox)
        elif shape_type == "ellipse":
            pyAether.emyEllipse.create(block, layer_num, purpose_num, bbox)
        elif shape_type == "polygon":
            points = [tuple(p) for p in params.get("points", [])]
            pyAether.emyPolygon.create(block, layer_num, purpose_num, points)
        elif shape_type == "arc":
            start_angle = params["start_angle"]
            stop_angle = params["stop_angle"]
            pyAether.emyArc.create(block, layer_num, purpose_num, bbox, start_angle, stop_angle)
        else:
            return ToolResult(data={"error": f"Unknown shape type: {shape_type}"})

        return ToolResult(data={"action": "create_shape", "shape_type": shape_type})

    async def _delete(self, pyAether: Any, block: Any, params: Dict[str, Any]) -> ToolResult:
        # Simplified: real implementation would need object references
        return ToolResult(data={"action": "delete", "note": "Delete requires object handles — use specific APIs"})


class SchematicCheckTool(EDATool):
    """Run schematic checks (connectivity, hierarchy, etc.)."""

    name = "schematic_check"
    aliases = ["sch_check", "check_schematic"]
    input_schema = {
        "type": "object",
        "properties": {
            "check_type": {
                "type": "string",
                "enum": ["connectivity", "hierarchy", "all"],
                "default": "all",
            },
        },
    }
    requires_design_open = True
    is_read_only = True

    def description(self) -> str:
        return "Run schematic validation checks: connectivity, hierarchy, and design rule checks."

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        try:
            import pyAether
        except ImportError:
            return ToolResult(data={"error": "pyAether is not available."})

        design = getattr(context, "active_design", None)
        if design is None:
            return ToolResult(data={"error": "No active design."})

        check_type = args.get("check_type", "all")

        try:
            results = {"check_type": check_type, "issues": []}

            if check_type in ("hierarchy", "all"):
                try:
                    if hasattr(pyAether, "aeCheckHierarchy"):
                        pyAether.aeCheckHierarchy()
                        results["hierarchy"] = "passed"
                    else:
                        results["hierarchy"] = "unavailable: aeCheckHierarchy not in EDA SDK"
                except Exception as e:
                    results["hierarchy"] = f"failed: {e}"

            if check_type in ("connectivity", "all"):
                try:
                    if hasattr(pyAether, "aeCheckDesign"):
                        pyAether.aeCheckDesign()
                        results["connectivity"] = "passed"
                    else:
                        results["connectivity"] = "unavailable: aeCheckDesign not in EDA SDK"
                except Exception as e:
                    results["connectivity"] = f"failed: {e}"

            return ToolResult(data=results)
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class SchematicNetlistTool(EDATool):
    """Generate a SPICE/Spectre/Verilog netlist from the schematic view."""

    name = "schematic_netlist"
    aliases = ["sch_netlist", "netlist_export"]
    input_schema = {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["spectre", "spice", "verilog", "vhdl"],
                "description": "Netlist output format.",
                "default": "spectre",
            },
            "output_path": {
                "type": "string",
                "description": "Optional path to write the netlist file. If omitted, returns inline.",
            },
            "top_cell": {
                "type": "string",
                "description": "Top-level cell name. Defaults to active cell.",
            },
            "include_parasitics": {
                "type": "boolean",
                "description": "Include parasitic elements in netlist.",
                "default": False,
            },
        },
    }
    requires_design_open = True

    def description(self) -> str:
        return (
            "Generate a SPICE/Spectre/Verilog netlist from the current schematic view. "
            "Can write to a file or return inline. Use this before simulation to produce "
            "the netlist that the simulator consumes."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        try:
            import pyAether
        except ImportError:
            return ToolResult(data={"error": "pyAether is not available."})

        design = getattr(context, "active_design", None)
        if design is None:
            return ToolResult(data={"error": "No active design."})

        fmt = args.get("format", "spectre")
        output_path = args.get("output_path", "")
        top_cell = args.get("top_cell", getattr(context, "active_cell", ""))
        include_parasitics = args.get("include_parasitics", False)

        try:
            # Map format to pyAether netlist function (if available)
            netlist_fn_map = {
                "spectre": getattr(pyAether, "aeCreateSpectreNetlist", None),
                "spice": getattr(pyAether, "aeCreateSpiceNetlist", None),
                "verilog": getattr(pyAether, "aeCreateVerilogNetlist", None),
                "vhdl": getattr(pyAether, "aeCreateVhdlNetlist", None),
            }
            netlist_fn = netlist_fn_map.get(fmt)

            if netlist_fn is None:
                return ToolResult(data={
                    "error": f"Netlist format '{fmt}' is not supported by the installed pyAether version.",
                    "available_formats": [k for k, v in netlist_fn_map.items() if v is not None] or "none",
                })

            kwargs = {"topCell": top_cell} if top_cell else {}
            if include_parasitics and hasattr(pyAether, "aeSetNetlistOption"):
                pyAether.aeSetNetlistOption("includeParasitics", True)

            netlist_content = netlist_fn(**kwargs)

            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(netlist_content)
                return ToolResult(data={
                    "format": fmt,
                    "top_cell": top_cell,
                    "output_path": output_path,
                    "line_count": netlist_content.count("\n"),
                    "message": f"Netlist written to {output_path}",
                })
            else:
                return ToolResult(data={
                    "format": fmt,
                    "top_cell": top_cell,
                    "netlist": netlist_content[:5000] + ("..." if len(netlist_content) > 5000 else ""),
                    "line_count": netlist_content.count("\n"),
                    "truncated": len(netlist_content) > 5000,
                })
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class SymbolEditTool(EDATool):
    """Create or edit schematic symbols (cell symbols / component symbols)."""

    name = "symbol_edit"
    aliases = ["sym_edit", "edit_symbol"]
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "edit", "add_pin", "add_shape", "add_text", "resize", "delete"],
                "description": "Symbol editing action.",
            },
            "cell_name": {
                "type": "string",
                "description": "Cell to create/edit symbol for. Defaults to active cell.",
            },
            "params": {
                "type": "object",
                "description": "Action-specific parameters (pin names, shapes, text, etc.).",
            },
        },
        "required": ["action"],
    }
    requires_design_open = True

    def description(self) -> str:
        return (
            "Create or edit the symbol view of a cell. Actions: create (new symbol), "
            "edit (modify existing), add_pin (add terminal pin), add_shape (rectangle, line, circle), "
            "add_text (label), resize (bounding box), delete (remove element). "
            "Used to create reusable component symbols for schematic capture."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        try:
            import pyAether
        except ImportError:
            return ToolResult(data={"error": "pyAether is not available."})

        design = getattr(context, "active_design", None)
        if design is None:
            return ToolResult(data={"error": "No active design."})

        action = args.get("action", "edit")
        cell_name = args.get("cell_name", getattr(context, "active_cell", ""))
        params = args.get("params", {})

        try:
            if action == "create":
                fn = getattr(pyAether, "aeCreateSymbol", None)
                if fn:
                    fn(cell_name)
                    return ToolResult(data={"action": "create", "cell": cell_name, "status": "symbol view created"})
                else:
                    return ToolResult(data={"action": "create", "cell": cell_name, "status": "unavailable", "note": "aeCreateSymbol not in EDA SDK"})
            elif action == "add_pin":
                pin_name = params.get("pin_name", "")
                direction = params.get("direction", "input")
                fn = getattr(pyAether, "aeSymbolAddPin", None)
                if fn:
                    fn(pin_name, direction)
                    return ToolResult(data={"action": "add_pin", "pin": pin_name, "direction": direction})
                else:
                    return ToolResult(data={"action": "add_pin", "status": "unavailable", "note": "aeSymbolAddPin not in EDA SDK"})
            elif action == "add_shape":
                shape_type = params.get("shape_type", "rect")
                fn = getattr(pyAether, "aeSymbolAddShape", None)
                if fn:
                    fn(shape_type)
                    return ToolResult(data={"action": "add_shape", "shape": shape_type})
                else:
                    return ToolResult(data={"action": "add_shape", "status": "unavailable", "note": "aeSymbolAddShape not in EDA SDK"})
            elif action == "add_text":
                text = params.get("text", "")
                fn = getattr(pyAether, "aeSymbolAddText", None)
                if fn:
                    fn(text)
                    return ToolResult(data={"action": "add_text", "text": text})
                else:
                    return ToolResult(data={"action": "add_text", "status": "unavailable", "note": "aeSymbolAddText not in EDA SDK"})
            elif action == "resize":
                width = params.get("width", 100)
                height = params.get("height", 100)
                fn = getattr(pyAether, "aeSymbolResize", None)
                if fn:
                    fn(width, height)
                    return ToolResult(data={"action": "resize", "width": width, "height": height})
                else:
                    return ToolResult(data={"action": "resize", "status": "unavailable", "note": "aeSymbolResize not in EDA SDK"})
            elif action == "delete":
                fn = getattr(pyAether, "aeSymbolDelete", None)
                if fn:
                    element_id = params.get("element_id", "")
                    fn(element_id)
                    return ToolResult(data={"action": "delete", "element_id": element_id})
                else:
                    return ToolResult(data={"action": "delete", "status": "unavailable", "note": "aeSymbolDelete not in EDA SDK"})
            else:
                return ToolResult(data={"error": f"Unknown symbol action: {action}"})
        except Exception as e:
            return ToolResult(data={"error": str(e)})
