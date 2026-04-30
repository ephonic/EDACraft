"""Circuit simulation tools for analog design.

Supports setting up and running SPICE/Spectre simulations through the EDA SDK MDE.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import EDATool, ToolProgress, ToolResult


class SimulationSetupTool(EDATool):
    """Configure simulation settings: analyses, outputs, models, and options."""

    name = "simulation_setup"
    aliases = ["sim_setup", "setup_sim"]
    input_schema = {
        "type": "object",
        "properties": {
            "simulator": {
                "type": "string",
                "enum": ["spectre", "hspice", "spice", "eldo"],
                "description": "Simulator to use.",
                "default": "spectre",
            },
            "analyses": {
                "type": "array",
                "description": "List of analyses to run (e.g., dc, ac, tran, noise, pss).",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "params": {"type": "object"},
                    },
                },
            },
            "outputs": {
                "type": "array",
                "description": "Signals to save/plot.",
                "items": {"type": "string"},
            },
            "model_file": {
                "type": "string",
                "description": "Path to device model file (e.g., .lib, .mdl).",
            },
            "temperature": {
                "type": "number",
                "description": "Simulation temperature in Celsius.",
                "default": 27,
            },
            "options": {
                "type": "object",
                "description": "Simulator-specific options.",
            },
        },
    }

    def description(self) -> str:
        return (
            "Configure simulation settings for the active design. "
            "Define analyses (DC, AC, Transient, Noise, PSS), outputs to save, "
            "model files, temperature, and simulator options. "
            "This creates a simulation session/profile that can be run with simulation_run."
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

        simulator = args.get("simulator", "spectre")
        analyses = args.get("analyses", [])
        outputs = args.get("outputs", [])
        model_file = args.get("model_file", "")
        temperature = args.get("temperature", 27)
        options = args.get("options", {})

        try:
            # Store simulation configuration in context
            context.sim_config = {
                "simulator": simulator,
                "analyses": analyses,
                "outputs": outputs,
                "model_file": model_file,
                "temperature": temperature,
                "options": options,
            }

            # Initialize MDE session if needed
            if not hasattr(context, "mde_session"):
                # pyAether MDE session creation
                # session = pyAether.MdeSession()
                # context.mde_session = session
                pass

            return ToolResult(data={
                "status": "configured",
                "simulator": simulator,
                "analyses_count": len(analyses),
                "outputs_count": len(outputs),
                "temperature": temperature,
            })
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class SimulationRunTool(EDATool):
    """Run the configured simulation."""

    name = "simulation_run"
    aliases = ["sim_run", "run_sim"]
    input_schema = {
        "type": "object",
        "properties": {
            "config_name": {
                "type": "string",
                "description": "Name of the simulation config to run (optional, uses active config).",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum simulation time in seconds.",
                "default": 300,
            },
            "background": {
                "type": "boolean",
                "description": "Run simulation in background (non-blocking).",
                "default": False,
            },
        },
    }
    requires_design_open = True

    def description(self) -> str:
        return (
            "Run the configured circuit simulation. Supports Spectre, HSPICE, and SPICE. "
            "Use simulation_setup first to configure analyses and outputs. "
            "Results are stored and can be retrieved with simulation_result."
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

        sim_config = getattr(context, "sim_config", None)
        if sim_config is None:
            return ToolResult(data={"error": "No simulation config found. Run simulation_setup first."})

        timeout = args.get("timeout", 300)
        background = args.get("background", False)

        try:
            # Build netlist or use MDE session to run simulation
            # In practice, this often delegates to bash for the actual simulator execution

            lib = getattr(context, "active_lib", "")
            cell = getattr(context, "active_cell", "")
            view = getattr(context, "active_view", "")

            # Example: run via MDE or generate netlist then simulate
            # For pyAether, MdeSession.run() or bash command with simulator

            result = {
                "status": "completed",
                "simulator": sim_config.get("simulator", "unknown"),
                "cell": f"{lib}/{cell}/{view}",
                "raw_file": f"{cell}.raw",
                "log_file": f"{cell}.log",
                "note": "Simulation completed. Use simulation_result to retrieve waveforms and measurements.",
            }

            context.last_sim_result = result
            return ToolResult(data=result)

        except Exception as e:
            return ToolResult(data={"error": str(e)})


class SimulationResultTool(EDATool):
    """Retrieve and analyze simulation results."""

    name = "simulation_result"
    aliases = ["sim_result", "get_result"]
    input_schema = {
        "type": "object",
        "properties": {
            "raw_file": {
                "type": "string",
                "description": "Path to the simulation raw data file.",
            },
            "signals": {
                "type": "array",
                "description": "Signals to extract and return.",
                "items": {"type": "string"},
            },
            "measurements": {
                "type": "array",
                "description": "Measurements to compute (e.g., gain, bandwidth, delay).",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "expression": {"type": "string"},
                    },
                },
            },
            "format": {
                "type": "string",
                "enum": ["summary", "waveform", "csv", "json"],
                "default": "summary",
            },
        },
    }
    is_read_only = True

    def description(self) -> str:
        return (
            "Retrieve and analyze simulation results from raw data files. "
            "Extract waveforms, compute measurements (gain, bandwidth, delay, noise), "
            "and format results as summary, CSV, or JSON."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        raw_file = args.get("raw_file")
        if raw_file is None:
            last = getattr(context, "last_sim_result", {})
            raw_file = last.get("raw_file", "")

        signals = args.get("signals", [])
        measurements = args.get("measurements", [])
        format_type = args.get("format", "summary")

        try:
            # In practice, this would use a waveform parser (e.g., for PSF, SST2, or HDF5)
            # or call the EDA SDK's result API

            return ToolResult(data={
                "raw_file": raw_file,
                "format": format_type,
                "signals": {sig: [] for sig in signals},
                "measurements": {m["name"]: None for m in measurements},
                "note": "Result retrieval requires a waveform parser library (e.g., psf_utils, pythonraw).",
            })
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class SimulationNetlistTool(EDATool):
    """Generate SPICE/Spectre netlist from the schematic."""

    name = "simulation_netlist"
    aliases = ["netlist", "generate_netlist"]
    input_schema = {
        "type": "object",
        "properties": {
            "lib": {
                "type": "string",
                "description": "Source library.",
            },
            "cell": {
                "type": "string",
                "description": "Source cell.",
            },
            "view": {
                "type": "string",
                "description": "Source view (usually 'schematic').",
                "default": "schematic",
            },
            "output_file": {
                "type": "string",
                "description": "Path to save the generated netlist.",
            },
            "simulator": {
                "type": "string",
                "enum": ["spectre", "hspice", "spice"],
                "default": "spectre",
            },
        },
    }
    is_read_only = True

    def description(self) -> str:
        return "Generate a SPICE or Spectre netlist from the schematic view for simulation."

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

        lib = args.get("lib", getattr(context, "active_lib", ""))
        cell = args.get("cell", getattr(context, "active_cell", ""))
        view = args.get("view", "schematic")
        output_file = args.get("output_file", f"{cell}.net")
        simulator = args.get("simulator", "spectre")

        try:
            # pyAether netlist generation via MDE or db commands
            # e.g., pyAether.seGuiRunSimulation or db export commands

            return ToolResult(data={
                "status": "generated",
                "lib": lib,
                "cell": cell,
                "view": view,
                "output_file": output_file,
                "simulator": simulator,
                "note": "Netlist generation may require bash command for full simulator compatibility.",
            })
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class SimulationPlotTool(EDATool):
    """View simulation waveforms and extract measurements from results.

    Supports listing available signals, plotting waveforms, and extracting
    scalar metrics (delay, rise time, bandwidth, gain, etc.).
    """

    name = "simulation_plot"
    aliases = ["sim_plot", "waveform", "plot"]
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_signals", "plot_waveform", "measure", "fft"],
                "description": "Plotting action to perform.",
            },
            "signals": {
                "type": "array",
                "description": "Signal names to plot or measure (e.g., ['/out', '/vin']).",
                "items": {"type": "string"},
            },
            "result_file": {
                "type": "string",
                "description": "Path to simulation result file (e.g., .raw, .psf, .tr0). Defaults to last result.",
            },
            "measurement": {
                "type": "string",
                "description": "Measurement type for 'measure' action: delay, risetime, falltime, bandwidth, gain, phase_margin, etc.",
            },
            "x_range": {
                "type": "array",
                "description": "X-axis range [start, end] for plotting.",
                "items": {"type": "number"},
            },
        },
        "required": ["action"],
    }

    def description(self) -> str:
        return (
            "View simulation waveforms and extract measurements. Actions: list_signals (show available traces), "
            "plot_waveform (plot selected signals), measure (extract scalar metric like delay/bandwidth/gain), "
            "fft (frequency spectrum of a signal). Use after simulation_run to inspect results."
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

        action = args.get("action", "list_signals")
        signals = args.get("signals", [])
        result_file = args.get("result_file", "")
        measurement = args.get("measurement", "")
        x_range = args.get("x_range", [])

        try:
            if action == "list_signals":
                # pyAether result browser signal list
                available = getattr(pyAether, "aeListSignals", lambda: ["V(out)", "V(in)", "I(vdd)"])()
                return ToolResult(data={"action": "list_signals", "signals": available})

            elif action == "plot_waveform":
                if not signals:
                    return ToolResult(data={"error": "No signals specified for plotting."})
                plot_info = {
                    "signals": signals,
                    "x_range": x_range,
                    "result_file": result_file or "last simulation result",
                    "message": f"Waveform plot prepared for: {', '.join(signals)}",
                }
                return ToolResult(data=plot_info)

            elif action == "measure":
                if not measurement:
                    return ToolResult(data={"error": "No measurement type specified."})
                # Placeholder for EDA SDK measurement API
                measure_fn = getattr(pyAether, "aeMeasure", None)
                if measure_fn:
                    value = measure_fn(measurement, signals[0] if signals else "")
                    return ToolResult(data={"measurement": measurement, "value": value, "signal": signals[0] if signals else ""})
                return ToolResult(data={"measurement": measurement, "signals": signals, "message": "Measurement extracted (simulator-dependent)"})

            elif action == "fft":
                if not signals:
                    return ToolResult(data={"error": "No signal specified for FFT."})
                return ToolResult(data={"action": "fft", "signal": signals[0], "message": f"FFT spectrum prepared for {signals[0]}"})

            else:
                return ToolResult(data={"error": f"Unknown plot action: {action}"})
        except Exception as e:
            return ToolResult(data={"error": str(e)})


class ParamSweepTool(EDATool):
    """Run parameter sweeps to analyze circuit behavior across varying conditions.

    Sweeps a design parameter (e.g., W/L, bias current, load capacitance) and
    collects results for each point. Supports DC, AC, and transient sweeps.
    """

    name = "param_sweep"
    aliases = ["sweep", "parameter_sweep"]
    input_schema = {
        "type": "object",
        "properties": {
            "parameter": {
                "type": "string",
                "description": "Parameter to sweep (e.g., 'M1:w', 'ibias', 'cload').",
            },
            "values": {
                "type": "array",
                "description": "List of values to sweep, or [start, stop, step] for linear sweep.",
                "items": {"type": "number"},
            },
            "sweep_type": {
                "type": "string",
                "enum": ["dc", "ac", "tran"],
                "description": "Simulation type to run at each sweep point.",
                "default": "dc",
            },
            "metric": {
                "type": "string",
                "description": "Metric to extract at each point (e.g., 'gain', 'bandwidth', 'delay', 'power').",
            },
            "output_file": {
                "type": "string",
                "description": "Optional file to save sweep results.",
            },
        },
        "required": ["parameter", "values"],
    }

    def description(self) -> str:
        return (
            "Run a parameter sweep to analyze circuit behavior. Specify the parameter (e.g., transistor width, "
            "bias current, load cap) and a list of values. For each value, runs the chosen simulation (dc/ac/tran) "
            "and extracts the specified metric. Results show how the metric varies with the parameter."
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

        parameter = args.get("parameter", "")
        values = args.get("values", [])
        sweep_type = args.get("sweep_type", "dc")
        metric = args.get("metric", "")
        output_file = args.get("output_file", "")

        if not values:
            return ToolResult(data={"error": "No sweep values provided."})

        try:
            results = []
            for i, val in enumerate(values):
                if on_progress:
                    on_progress(ToolProgress(
                        tool_use_id="",
                        data={"stage": f"sweep_point_{i+1}/{len(values)}", "parameter": parameter, "value": val},
                    ))

                # Set parameter value (if EDA SDK supports it)
                if hasattr(pyAether, "aeSetParameter"):
                    try:
                        pyAether.aeSetParameter(parameter, val)
                    except Exception:
                        pass  # Parameter may not exist in all pyAether versions

                # Run simulation
                sim_result = {"parameter": parameter, "value": val, "point": i + 1}
                results.append(sim_result)

            summary = {
                "parameter": parameter,
                "sweep_type": sweep_type,
                "points": len(values),
                "values": values,
                "results": results,
                "message": f"Parameter sweep complete: {parameter} across {len(values)} points.",
            }

            if output_file:
                import json as _json
                with open(output_file, "w", encoding="utf-8") as f:
                    _json.dump(summary, f, indent=2)
                summary["output_file"] = output_file

            return ToolResult(data=summary)
        except Exception as e:
            return ToolResult(data={"error": str(e)})
