"""Core Agent engine for EDA Agent.

Manages the conversation loop, tool execution, and context state.
Inspired by Claude Code's QueryEngine, adapted for Python and EDA workflows.

Features:
- Context-aware conversation with token budgeting
- Automatic context compaction when approaching budget limits
- Progress streaming for tool execution
- Design state persistence across turns
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from eda_agent.core.context import AgentContext
from eda_agent.core.context_manager import CompactionResult, ContextManager
from eda_agent.core.knowledge_base import KnowledgeBase
from eda_agent.providers.base import BaseProvider, Message
from eda_agent.tools.base import BaseTool, EDATool, ToolProgress, ToolResult
from eda_agent.tools.background_tools import BackgroundTaskManager
from eda_agent.tools.registry import ToolRegistry, get_default_registry


class AgentPhase:
    """Explicit phase states for the agent conversation flow.

    Each user request goes through a clear three-stage pipeline:
    ANALYZING → EXECUTING → RESPONDING
    """
    ANALYZING = "analyzing"
    EXECUTING = "executing"
    RESPONDING = "responding"


class EDAAgent:
    """The main agent orchestrator.

    Coordinates between the LLM provider, tool registry, and execution context
    to handle user requests for analog circuit design tasks.
    """

    # General-purpose tools available for ALL queries.
    # EDA operations are done via Python scripts (file_write + bash), not direct tool calls.
    GENERAL_TOOL_NAMES: List[str] = [
        "bash", "file_read", "file_write", "file_edit", "glob", "grep",
        "diff", "task_plan", "set_todo_list",
        "background_submit", "background_status", "background_results",
    ]

    # Required parameters for key tools. Used for pre-validation to catch
    # empty tool calls BEFORE they consume a tool round.
    _REQUIRED_PARAMS: Dict[str, List[str]] = {
        "file_write": ["path", "content"],
        "file_edit": ["path", "old_string", "new_string"],
        "bash": ["command"],
        "file_read": ["path"],
        "glob": ["pattern"],
        "grep": ["pattern", "path"],
        "diff": ["path_a", "path_b"],
    }

    @staticmethod
    def summarize_tool_args(name: str, args: Dict[str, Any], raw_args: str = "") -> str:
        """Generate a one-line summary of tool arguments for UI display."""
        # Fallback: if args is empty/malformed but raw JSON string is available,
        # try a lightweight regex extraction for the most common fields.
        if (not args or not isinstance(args, dict)) and raw_args and raw_args not in ("", "{}"):
            import re
            if name == "bash":
                m = re.search(r'"command"\s*:\s*"([^"]+)"', raw_args)
                if m:
                    cmd = m.group(1)
                    return cmd[:60] + ("..." if len(cmd) > 60 else "")
            if name in ("file_read", "file_write", "file_edit"):
                m = re.search(r'"(?:path|file_path)"\s*:\s*"([^"]+)"', raw_args)
                if m:
                    return f"file: {m.group(1)[:60]}"
            if name == "glob":
                m = re.search(r'"(?:pattern|path)"\s*:\s*"([^"]+)"', raw_args)
                if m:
                    return f"pattern: {m.group(1)[:60]}"
            if name == "grep":
                m1 = re.search(r'"pattern"\s*:\s*"([^"]+)"', raw_args)
                m2 = re.search(r'"path"\s*:\s*"([^"]+)"', raw_args)
                pat = m1.group(1) if m1 else ""
                pth = m2.group(1) if m2 else ""
                return f"pattern: {pat}" + (f" in {pth}" if pth else "")
            return ""

        if not args or not isinstance(args, dict):
            return ""
        # File tools
        if name in ("file_read", "file_write", "file_edit"):
            path = args.get("path") or args.get("file_path") or ""
            return f"file: {path}" if path else ""
        if name == "glob":
            pattern = args.get("pattern") or args.get("path") or ""
            return f"pattern: {pattern}" if pattern else ""
        if name == "grep":
            pattern = args.get("pattern") or ""
            path = args.get("path") or ""
            return f"pattern: {pattern}" + (f" in {path}" if path else "")
        # Bash
        if name == "bash":
            cmd = args.get("command") or ""
            return cmd[:60] + ("..." if len(cmd) > 60 else "") if cmd else ""
        # EDA design tools
        if name in ("design_open", "design_create"):
            d = args.get("design_name") or args.get("lib_name") or ""
            return f"design: {d}" if d else ""
        if name in ("schematic_edit", "layout_edit", "layout_place", "layout_route"):
            c = args.get("cell_name") or args.get("cell") or ""
            return f"cell: {c}" if c else ""
        if name == "simulation_run":
            f = args.get("netlist_file") or args.get("testbench") or ""
            return f"netlist: {f}" if f else ""
        if name in ("drc_run", "lvs_run"):
            c = args.get("cell_name") or args.get("layout_view") or ""
            return f"cell: {c}" if c else ""
        if name == "circuit_harness":
            c = args.get("cell_name") or ""
            return f"cell: {c}" if c else ""
        if name == "pex_run":
            c = args.get("cell_name") or ""
            return f"cell: {c}" if c else ""
        # Fallback: show first key-value pair
        for k, v in args.items():
            if v and k not in ("description", "detail", "verbose"):
                val = str(v)
                return f"{k}: {val[:40]}" + ("..." if len(val) > 40 else "")
        return ""

    @staticmethod
    def _response_contains_unsaved_code(content: Optional[str], successful_tools: List[str]) -> bool:
        """Detect if the model output code in text without calling file_write.

        This is a safety net to catch the common failure mode where the model
        outputs a complete script in markdown instead of calling file_write.
        """
        if not content:
            return False

        # Only skip if file_write/file_edit SUCCESSFULLY wrote a file.
        # Failed calls don't count — the safety net should still trigger.
        if "file_write" in successful_tools or "file_edit" in successful_tools:
            return False

        # Look for fenced code blocks OR inline code snippets
        import re

        # 1. Match ```python ... ``` or ``` ... ``` blocks
        code_blocks = re.findall(r"```(?:\w+)?\s*(.*?)\s*```", content, re.DOTALL)

        # 2. Also detect plain-text code: lines starting with import/def/class
        # This catches code the model outputs without fences
        plain_code_lines = re.findall(
            r"(?:^|\n)(import\s+\w+|from\s+\w+\s+import|def\s+\w+|class\s+\w+|if\s+__name__\s*==)",
            content,
        )

        all_blocks = [b.strip() for b in code_blocks if len(b.strip()) >= 30]
        # If plain code lines exist AND there's a substantial block of text that looks like code
        if plain_code_lines:
            # Find contiguous lines that look like code
            lines = content.splitlines()
            code_line_count = sum(
                1 for line in lines
                if re.match(r"^\s*(import |from |def |class |if |for |while |print\(|# |\"\"\"|''')", line)
            )
            if code_line_count >= 5:
                all_blocks.append(content)  # Treat entire reply as a code block

        if not all_blocks:
            return False

        # Check if any block looks like a script
        for block in all_blocks:
            if len(block) < 50:
                continue
            if any(kw in block for kw in ("import ", "def ", "class ", "if __name__")):
                return True
            if any(kw in block for kw in ("cd ", "python", "bash ", "./")) and "\n" in block:
                return True

        return False

    async def _auto_execute_code_from_response(
        self,
        content: Optional[str],
        successful_tools: List[str],
        tools_used: List[str],
        on_progress: Optional[Callable[[str, Any], None]] = None,
    ) -> bool:
        """ULTIMATE SAFETY NET: Auto-extract code from response, write it, and execute it.

        When the model outputs code in its reply but refuses to call file_write/bash,
        the backend does it automatically. This bypasses the model's tendency to
        behave like a chatbot instead of an execution agent.

        Guard rails:
        - Max 2 auto-executions per conversation (prevents infinite loops)
        - Detects identical code blocks across iterations (prevents re-executing same broken code)
        - Bash timeout is 30s (prevents hanging on interactive or GUI code)

        Returns True if code was found and auto-executed.
        """
        if not content:
            return False

        # Only skip if file_write/file_edit SUCCESSFULLY wrote a file.
        # Failed calls don't count — the safety net should still trigger.
        if "file_write" in successful_tools or "file_edit" in successful_tools:
            return False

        # Hard limit: max 2 auto-executions to prevent infinite loops
        if self._auto_execute_count >= 2:
            return False

        import re
        import time
        import hashlib

        # Extract all fenced code blocks with their language tags (relaxed)
        code_blocks = re.findall(r"```(\w+)?\s*(.*?)\s*```", content, re.DOTALL)
        if not code_blocks:
            return False

        # Find the best candidate: longest block that looks like a real script
        best_block = None
        best_lang = None
        for lang, block in code_blocks:
            block = block.strip()
            if len(block) < 50:
                continue
            score = 0
            if lang and lang.lower() in ("python", "py"):
                score += 100
            if any(kw in block for kw in ("import ", "def ", "class ", "if __name__")):
                score += 50
            if "print(" in block:
                score += 20
            if lang and lang.lower() in ("bash", "sh", "shell"):
                score += 80
            if score > 0 and (best_block is None or len(block) > len(best_block)):
                best_block = block
                best_lang = lang or "python"

        if not best_block:
            return False

        # Detect loop: same code block as last auto-execution
        current_hash = hashlib.md5(best_block.encode("utf-8")).hexdigest()[:16]
        if current_hash == self._last_auto_executed_code_hash:
            return False  # Same broken code again, stop looping
        self._last_auto_executed_code_hash = current_hash

        # Infer filename from surrounding text
        filepath = None
        first_block_pos = content.find("```")
        before_text = content[:first_block_pos] if first_block_pos > 0 else content
        # Determine save directory from context project_root
        save_dir = getattr(self.context, "project_root", os.getcwd()) or os.getcwd()
        # Look for explicit filename mentions
        filename_match = re.search(r"[\"']?(\w[\w_\-]*\.(?:py|sh))", before_text)
        if filename_match:
            filepath = os.path.join(save_dir, filename_match.group(1))
        else:
            ext = "sh" if best_lang and best_lang.lower() in ("bash", "sh", "shell") else "py"
            filepath = os.path.join(save_dir, f"eda_auto_{int(time.time())}.{ext}")

        # Determine execution command
        if best_lang and best_lang.lower() in ("bash", "sh", "shell"):
            exec_cmd = f"bash {filepath}"
        else:
            exec_cmd = f"python3 {filepath}"

        # Also look for explicit execution instructions in the text (e.g., "cd /path && python3 file.py")
        exec_match = re.search(
            r"(?:run|execute|cd\s+[\w/._-]+\s*(?:&&|;|\n)\s*)+(?:python3?|bash)\s+[\w/._-]+",
            content,
            re.IGNORECASE,
        )
        if exec_match:
            explicit_cmd = exec_match.group(0)
            # Replace the filename in explicit command with our absolute path
            explicit_cmd = re.sub(r"(?:python3?|bash)\s+\S+\.(?:py|sh)", f"python3 {filepath}" if ext == "py" else f"bash {filepath}", explicit_cmd)
            exec_cmd = explicit_cmd

        if on_progress:
            on_progress("status", {
                "status": "auto_executing",
                "message": f"Auto-extracting code → {filepath} → executing...",
            })

        # Step 1: Auto file_write
        try:
            file_result = await self._execute_tool(
                "file_write",
                {"path": filepath, "content": best_block},
                f"auto_file_write_{int(time.time())}",
                on_progress,
            )
            self._context_manager.add_tool_result(
                content=file_result.data,
                tool_call_id=f"auto_file_write_{int(time.time())}",
                name="file_write",
            )
        except Exception as e:
            self._context_manager.add_tool_result(
                content={"error": f"Auto file_write failed: {e}"},
                tool_call_id=f"auto_file_write_{int(time.time())}",
                name="file_write",
            )
            return False

        # Step 2: Auto bash execute (short timeout to prevent hanging)
        try:
            bash_result = await self._execute_tool(
                "bash",
                {"command": exec_cmd, "timeout": 30000},
                f"auto_bash_{int(time.time())}",
                on_progress,
            )
            self._context_manager.add_tool_result(
                content=bash_result.data,
                tool_call_id=f"auto_bash_{int(time.time())}",
                name="bash",
            )
        except Exception as e:
            self._context_manager.add_tool_result(
                content={"error": f"Auto bash failed: {e}"},
                tool_call_id=f"auto_bash_{int(time.time())}",
                name="bash",
            )

        # Step 3: Increment counter, update tools_used, and inject nudge
        self._auto_execute_count += 1
        if "file_write" not in tools_used:
            tools_used.append("file_write")
        if "bash" not in tools_used:
            tools_used.append("bash")
        nudge = (
            f"The code has been automatically saved to {filepath} and executed. "
            f"Review the execution results above. If successful, continue with the next steps. "
            f"If failed, analyze the error and call file_edit + bash to fix it."
        )
        self._context_manager.add_system_message(nudge)

        return True

    def __init__(
        self,
        provider: BaseProvider,
        registry: Optional[ToolRegistry] = None,
        context: Optional[AgentContext] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 25,
        max_tool_rounds: int = 50,
        max_tokens: int = 128000,
        auto_compact: bool = True,
    ) -> None:
        self.provider = provider
        self.registry = registry or get_default_registry()
        self.context = context or AgentContext()
        self.max_iterations = max_iterations
        self.max_tool_rounds = max_tool_rounds
        self.auto_compact = auto_compact
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._iteration = 0
        self._task_counter = 0
        self._cancel_event = asyncio.Event()
        self._auto_execute_count = 0
        self._last_auto_executed_code_hash = ""
        self._eda_api_injected = False
        self._common_knowledge_injected = False

        # Initialize conditional knowledge base (lazy-loads pyAE.md + ckt.md)
        project_root = getattr(self.context, "project_root", os.getcwd()) or os.getcwd()
        self._knowledge_base = KnowledgeBase.from_project_root(project_root)

        # Attach background task manager and registry to context for tool access
        if not hasattr(self.context, "background_task_manager") or self.context.background_task_manager is None:
            self.context.background_task_manager = BackgroundTaskManager()
        self.context.tool_registry = self.registry

        # Initialize context manager with token budgeting
        self._context_manager = ContextManager(
            system_prompt=self._system_prompt,
            max_tokens=max_tokens,
            reserve_tokens=8000,
            compaction_threshold=0.6,
            min_messages_before_compaction=4,
        )

        # Phase state for clear UI separation
        self._phase = AgentPhase.ANALYZING

    def _set_phase(
        self,
        phase: str,
        on_progress: Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        """Switch agent phase and notify frontend."""
        if self._phase == phase:
            return
        self._phase = phase
        if on_progress:
            on_progress("phase", {"phase": phase})

    def _maybe_update_plan(
        self,
        tool_name: str,
        on_progress: Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        """Update active plan progress after a tool execution."""
        if self.context.active_plan:
            self.context.update_plan_progress(tool_name)
            if on_progress:
                on_progress("plan_update", {"plan": self.context.active_plan})

    def _select_tools(self, user_input: str) -> List[Dict[str, Any]]:
        """Return all available tool schemas.

        All requests get the same general tools. EDA operations are performed
        by writing Python scripts (file_write) and executing them (bash),
        not by calling EDA-specific tools directly.
        """
        return self.registry.get_schemas_for_tools(self.GENERAL_TOOL_NAMES, compact=True)

    def _tools_desc_with_params(self) -> str:
        """Generate compact tool descriptions for the system prompt.

        Only lists tool name + short description. Required parameters are
        already emphasized in the CRITICAL rules section above, so we avoid
        repeating them here to reduce token count and first-request latency.
        """
        lines = []
        for name in self.GENERAL_TOOL_NAMES:
            t = self.registry.get(name)
            if not t:
                continue
            desc = BaseTool._compact_description(t.description())
            lines.append(f"- {t.name}: {desc}")
        return "\n".join(lines)

    @staticmethod
    def _is_eda_request(user_input: str) -> bool:
        """Detect if the user request involves EDA design work.

        Used to decide whether to inject the full EDA API Reference
        into the system prompt (lightweight prompt for non-EDA queries).
        """
        if not user_input:
            return False
        text = user_input.lower()
        eda_keywords = {
            # English
            "schematic", "layout", "simulation", "design", "circuit", "eda",
            "drc", "lvs", "pex", "netlist", "symbol", "cell", "library",
            "dbopenlib", "dbcreatelib", "dbnewcellview", "emy", "virtuoso",
            "cadence", "spice", "ngspice", "hspice", "spectre", "calibre",
            "guardring", "inst", "wire", "pin", "port", "gds",
            # Chinese
            "原理图", "版图", "仿真", "设计", "电路", "器件",
            "单元", "库", "符号", "连线", "器件", "偏置", "电流镜",
        }
        return any(kw in text for kw in eda_keywords)

    def _ensure_eda_api_injected(self, user_input: str) -> bool:
        """Inject EDA API reference if this is an EDA-related request.

        Returns True if injection occurred (or was already present).
        """
        if not self._is_eda_request(user_input):
            return False
        if self._eda_api_injected:
            return True
        injected = self._context_manager.inject_eda_api(self._eda_api_reference())
        if injected:
            self._eda_api_injected = True
        return self._eda_api_injected

    def _ensure_knowledge_injected(self, user_input: str) -> List[str]:
        """Conditionally inject relevant knowledge chunks based on user intent.

        This provides fine-grained knowledge injection:
        - Common EDA knowledge (always injected on first EDA request)
        - EDA SDK API chunks (matched by keywords from pyAE.md)
        - Circuit design chunks (matched by keywords from ckt.md)

        Only uninjected chunks are appended to avoid duplication.

        Returns:
            List of chunk IDs that were newly injected.
        """
        if not self._is_eda_request(user_input):
            return []

        newly_injected: List[str] = []

        # 1. Common knowledge — always inject once on first EDA request
        if not self._common_knowledge_injected:
            common_text = self._knowledge_base.get_common_knowledge()
            if self._context_manager.inject_knowledge(common_text, tag="common:eda"):
                self._common_knowledge_injected = True
                newly_injected.append("common:eda")

        # 2. Retrieve relevant chunks from both pyAE and ckt
        chunks = self._knowledge_base.retrieve(
            user_input,
            top_k=10,
            min_score=0.5,
            max_tokens=10000,
        )
        if not chunks:
            return newly_injected

        # 3. Inject only chunks not yet injected
        uninjected = self._knowledge_base.get_uninjected(chunks)
        for chunk in uninjected:
            if self._context_manager.inject_knowledge(chunk.content, tag=chunk.chunk_id):
                self._knowledge_base.mark_injected([chunk.chunk_id])
                newly_injected.append(chunk.chunk_id)

        return newly_injected

    def _eda_api_reference(self) -> str:
        """Return the full EDA API reference text.

        This is injected on-demand for EDA tasks to keep the base
        system prompt lightweight for general queries.
        """
        return """## EDA Python API Reference
All EDA operations are done by writing Python scripts that `import pyAether`.

The EDA SDK has two API styles:
1. **Legacy API** (`dbOpenLib`, `dbCreateInstByMasterName`, `dbCrtWire`, etc.) — simpler, direct string names, preferred for quick scripting
2. **Modern emy API** (`emyDesign.open`, `emyScalarInst.create`, etc.) — requires scalar names and namespaces

**Prefer the Legacy API for schematic/symbol scripting** — it is more concise and proven in production.

### Legacy API — Schematic/Symbol Workflow
```python
from pyAether import *

# 1. Open/create library
lib = dbOpenLib("hes")
if not lib:
    lib = dbCreateLib("hes")

# 2. Create schematic cellview (5 args: lib, cell, view, viewType, mode)
cv = dbNewCellView("hes", "opamp", "schematic", "schematic", "w")

# 3. Create terminals and nets
term = dbCrtTerm(cv, "VIN_P", "input")
net = dbCrtNet(cv, "VDD")

# 4. Place instance with parameters
inst = dbCreateInstByMasterName(
    cv, "hes", "n_mos", "symbol", "M1",
    [100, 200], "R0",
    [("w", "2.0"), ("l", "0.18"), ("m", "1")]
)

# 5. Connect instance terminal to net
inst_term = dbCrtInstTermByName(inst, "D")
dbAddFigToNet(inst_term, net)

# 6. Create wire on net
dbCrtWire(cv, net, [[100, 250], [200, 250]], 0.5)

# 7. Save
dbSaveCV(cv)
dbCloseCV(cv)
```

### Legacy API — Key Functions
- `dbOpenLib(name)` / `dbCreateLib(name)` — Library management
- `dbNewCellView(lib, cell, view, viewType, mode)` — Create cellview (5 args!)
- `dbSaveCV(cv)` / `dbCloseCV(cv)` — Save/close
- `dbCrtTerm(cv, name, direction)` — Create terminal (direction: "input"/"output"/"inputOutput")
- `dbFindTermByName(cv, name)` — Find existing terminal
- `dbCrtNet(cv, name)` — Create net
- `dbAddFigToNet(fig, net)` — Connect figure (term/instTerm) to net
- `dbCreateInstByMasterName(cv, lib, cell, view, name, origin, orient, params)` — Place instance. Params: list of `(name, value)` tuples as **strings**
- `dbCrtInstTermByName(inst, termName)` — Create instance terminal (e.g. "D", "G", "S", "B")
- `dbCrtWire(cv, net, points, width)` — Create wire (points: list of `[x,y]`)
- `dbCrtSymbolPin(cv, name, dir, point, orient)` — Symbol pin
- `dbCrtSymbolPolygon(cv, purpose, points)` — Symbol shape
- `dbCrtSymbolLabel(cv, purpose, text, point, align, orient)` — Symbol text

### Modern emy API — Layout/Advanced Workflow
```python
import pyAether
pyAether.emyInitDb()
ns = pyAether.emyUnixNS()
lib = pyAether.emyScalarName(ns, "mylib")
cell = pyAether.emyScalarName(ns, "inv1")
view = pyAether.emyScalarName(ns, "schematic")
design = pyAether.emyDesign.open(lib, cell, view, pyAether.emySchematic, "w")
block = pyAether.emyBlock.create(design)
# ... edit ...
design.save()
```

### Modern emy API — Key Functions
- `pyAether.emyInitDb()` — Initialize database
- `pyAether.emyUnixNS()` — Get namespace
- `pyAether.emyScalarName(ns, name)` — Create scalar name
- `pyAether.emyDesign.open(lib, cell, view, view_type, mode)` — Open design
- `pyAether.emyBlock.create(design)` — Create top block
- `pyAether.emyScalarInst.create(block, master, name, trans, params, ...)` — Place instance
- `pyAether.emyScalarNet.create(block, name, sigType, ...)` — Create net
- `pyAether.emyLine.create(block, layer, purpose, points)` — Create wire
- `pyAether.emyText.create(...)` — Create text label
- `pyAether.emyRect.create(...)` / `emyEllipse.create(...)` / `emyPolygon.create(...)` — Shapes
- `pyAether.dbCrtPath(design, layer, points, width)` — Layout path
- `pyAether.aeCrtGuardring(design, center_line, template, ...)` — Guard ring

### PDK Library Binding (required when creating design library)
```python
import pyAether as pa

# 1. Get the PDK tech library object (provided by foundry, e.g. "018um_PDK")
pdk_lib = pa.get_library("Your_PDK_Library_Name")

# 2. Create design library bound to PDK — CRITICAL: attach_tech_library parameter
my_design_lib = pa.create_library(
    name="my_design_lib",
    attach_tech_library=pdk_lib   # Binds design lib to PDK, inherits all tech info
)
```

### PDK Device Instantiation (for MOS and other PDK devices)
```python
import pyAether as pa

# 1. Get the target device cell from PDK
pdk_cell = pa.get_cell("Your_PDK_Library_Name", "nmos")

# 2. Open the target schematic for editing
target_sch = pa.get_schematic("my_design_lib", "top_cell")
target_sch.enter_edit()

# 3. Place instance from PDK cell at coordinates
instance = target_sch.add_instance(
    master=pdk_cell,      # PDK cell to instantiate
    name="M0",            # Instance name in schematic
    location=(10, 20)     # Placement coordinates
)

# 4. Set device parameters (e.g. W/L for transistors)
instance.set_parameter("w", "1u")      # Width = 1um
instance.set_parameter("l", "180n")    # Length = 180nm

# 5. Save and exit
target_sch.exit_edit()
```

### PDK Device Instantiation — Layout
```python
import pyAether as pa

layout_view = pa.get_schematic("my_design_lib", "inverter", "layout")
layout_view.enter_edit()

pdk_lib = pa.db.get_library("PDK_Library_Name")
pmos_cell = pdk_lib.get_cell("p18")
nmos_cell = pdk_lib.get_cell("n18")

pmos_inst = layout_view.add_instance(pmos_cell, name="MP0", location=(0, 0))
pmos_inst.set_parameter("w", "2u")
pmos_inst.set_parameter("l", "0.18u")
pmos_inst.set_parameter("m", "1")

nmos_inst = layout_view.add_instance(nmos_cell, name="MN0", location=(0, -5))
nmos_inst.set_parameter("w", "1u")
nmos_inst.set_parameter("l", "0.18u")
nmos_inst.set_parameter("m", "1")

layout_view.exit_edit()
```

### Netlist Export
- **Programmatic (recommended):** `netlist_func = pyAether.aeExportNetlistFunc()` then `netlist_func.funcInitCb(lib, cell, view, "output.sp")` — exports netlist to file without GUI.
- **GUI dialog:** `pyAether.mdeCrtNetlist()` — opens netlist generation dialog.
- **MDE Session (netlist+run):** `session = pyAether.MdeSession.open(lib, cell, state); session.netlistAndRun()`

### Netlist Verification (MUST do before simulation)
**ALWAYS check the netlist before simulating.** Unchecked netlists can produce wrong results or fail.
1. **Shorts** — nodes that shouldn't be connected (LVS failures, metal overlap)
2. **Opens** — nodes that should be connected but aren't (missing connections, unconnected instances)
3. **Floating nodes** — nodes with no driver, usually from:
   - MOS body (B) terminal not connected
   - Capacitor/resistor one end dangling
   - Differential signals missing common-mode bias
4. **Pin order errors** — D/G/S/B wrong, causing completely wrong results

**Quick check flow:**
- After exporting netlist → `grep -i -E "floating|unconnected|short|open" netlist.log`
- Verify key nodes: VDD, VSS, GND all connected; MOS bodies tied correctly
- If issues found → fix in schematic or edit .sp directly → re-export
- If clean → proceed to simulation

### Log File Inspection Strategy
**NEVER `file_read` an entire log file** (can be MBs). Instead:
1. `grep -i -n -E "error|warning|failed|fatal" output.log | head -50` to find issues
2. Based on grep results, use `sed -n '40,60p' output.log` to extract context
3. If grep finds nothing, the run was successful — no further reading needed

### Important Notes
- **Instance parameters** must be strings: `[("w", "2.0"), ("l", "0.18")]` not `[("w", 2.0)]`
- **dbNewCellView takes 5 arguments**: `(lib, cell, view, viewType, mode)` — do not omit the mode
- **dbCrtTerm takes cellview**, not a net object
- **dbOpenLib takes only name**, no mode parameter
- Orientations: `"R0"`, `"R90"`, `"R180"`, `"R270"`, `"MY"`, `"MX"`, `"MYR90"`, `"MXR90"` (Legacy) or `emcR0`, `emcR90`, etc. (Modern)

### How to Design with EDA SDK
- **Prefer Legacy API** for schematic and symbol creation — it is more concise
- **Use Modern API** for layout and when writing reusable tool code
- **Explore further**: You can discover additional SDK functions by writing exploratory scripts (e.g., `print(dir(pyAether))`, `help(pyAether.emyDesign.open)`) and running them with `bash`.
- **Write Python scripts** for ALL circuit design tasks: schematic creation, layout drawing, simulation setup, DRC/LVS checks, netlist extraction, etc.
- **Execute via python**: Always run your scripts with `python3 your_script.py` using the `bash` tool.
- **Tool Scope**: Use the tools and APIs available in this environment. Do not assume access to external EDA software.
"""

    def _default_system_prompt(self) -> str:
        """Generate the lightweight default system prompt.

        The heavy EDA API Reference is omitted here and injected
        on-demand via `_ensure_eda_api_injected()` for EDA-related queries.
        This keeps TTFT low for general-purpose questions.
        """
        tools_desc = self._tools_desc_with_params()

        return f"""You are EDA Agent, an expert analog circuit design assistant.

## Core Directive: ACT via tools, then reply with a brief summary (1-2 sentences).
- **NEVER** paste code in replies — use `file_write` to save, `bash` to run.
- **NEVER** tell users to run things manually — YOU write and execute.
- Max 50 tool rounds. Group related ops when possible.

### Tool Parameters (ALL required — never call with empty `{{}}`)
- `file_write`: `path` (string, file path), `content` (string, full file content)
- `file_edit`: `path` (string), `old_string` (string), `new_string` (string)
- `bash`: `command` (string)
- `file_read`: `path` (string) | `glob`/`grep`: `pattern` (string)

### Critical: file_write MUST include both `path` and `content`
Correct: `{"path": "/path/to/file.py", "content": "import os..."}`
WRONG: `{{}}` or `{"path": "/path/to/file.py"}` (missing content)

### EDA Task Workflow
1. WRITE Python script using EDA APIs → 2. SAVE via `file_write` → 3. RUN via `bash`
4. On errors: `file_read` error → `file_edit` fix → `bash` retry
5. Never call individual EDA functions as tools — they don't exist as tools.

## Available Tools
{tools_desc}

## Execution Rules
1. WRITE scripts → `file_write` → `bash` to execute.
2. Iterate on failure: `file_edit` + retry. Read errors with `file_read` if needed.
3. THINK briefly — one sentence before/after each tool. No essays.
4. "give me a plan" → `task_plan` only. "design/build/run" → plan then execute immediately.

Current context:
{self.context.to_prompt_context()}
"""

    @staticmethod
    def _normalize_tool_call_id(tc: Dict[str, Any]) -> str:
        """Extract or generate a stable tool call ID.

        Providers may omit or set None for tool_call IDs in streaming chunks.
        We generate a deterministic UUID on first access and store it back
        into the dict so streaming and execution phases share the same ID.
        """
        tid = tc.get("id")
        if tid:
            return str(tid)
        tid = str(uuid.uuid4())
        tc["id"] = tid
        return tid

    @property
    def messages(self) -> List[Message]:
        """Get current conversation messages."""
        return self._context_manager.messages

    def get_context_budget(self) -> Dict[str, Any]:
        """Get current token budget status."""
        return self._context_manager.get_budget_status()

    async def compact_context(self) -> CompactionResult:
        """Manually trigger context compaction.

        Returns:
            CompactionResult with statistics about the operation.
        """
        result = self._context_manager.compact(provider=self.provider)
        return result

    async def _ensure_context_budget(
        self,
        on_progress: Optional[Callable[[str, Any], None]] = None,
    ) -> Optional[str]:
        """Ensure context is within budget. Auto-compact if over threshold.

        Two-stage compaction:
        1. Standard compaction — summarize old messages, keep recent context.
        2. Aggressive compaction — if standard is insufficient, keep only
           system + last 2 messages.

        Returns:
            Error message if budget cannot be brought under control, None otherwise.
        """
        if not self.auto_compact:
            return None

        budget = self._context_manager.get_budget_status()
        if budget["usage_ratio"] < self._context_manager.compaction_threshold:
            return None

        # ── Stage 1: Standard compaction ──
        if on_progress:
            on_progress("status", {"status": "compacting", "message": f"Context budget {budget['usage_ratio']:.0%}, compacting..."})

        result = self._context_manager.force_compact(provider=self.provider)

        if result.success and on_progress:
            on_progress("compaction", {
                "tokens_saved": result.tokens_saved,
                "original_count": result.original_count,
                "compacted_count": result.compacted_count,
                "mode": "standard",
            })

        # Check again after standard compaction
        budget = self._context_manager.get_budget_status()
        if budget["usage_ratio"] < self._context_manager.compaction_threshold:
            return None

        # ── Stage 2: Aggressive compaction ──
        if on_progress:
            on_progress("status", {"status": "compacting", "message": "Standard compaction insufficient, performing aggressive compaction..."})

        result = self._context_manager.force_compact_aggressive(provider=self.provider)

        if result.success and on_progress:
            on_progress("compaction", {
                "tokens_saved": result.tokens_saved,
                "original_count": result.original_count,
                "compacted_count": result.compacted_count,
                "mode": "aggressive",
            })

        # Final check
        budget = self._context_manager.get_budget_status()
        if budget["usage_ratio"] >= self._context_manager.compaction_threshold:
            return (
                f"⚠️ Context budget critical: {budget['usage_ratio']:.0%} used "
                f"({budget['current_tokens']}/{budget['available_tokens']} tokens). "
                f"System: {budget['system_tokens']} tokens, "
                f"Messages: {budget['message_count']}, "
                f"Compactions: {budget['compaction_count']}. "
                f"Both standard and aggressive compaction were performed but could not "
                f"free enough space. Please start a new chat to continue."
            )
        return None

    def reset(self) -> None:
        """Reset the conversation history."""
        self._context_manager.reset()
        self._iteration = 0
        self._cancel_event.clear()
        self._eda_api_injected = False
        self._common_knowledge_injected = False
        self._knowledge_base.reset_injection_state()

    def cancel(self) -> None:
        """Signal the agent to stop the current operation."""
        self._cancel_event.set()

    async def run(
        self,
        user_input: str,
        on_progress: Optional[Callable[[str, Any], None]] = None,
    ) -> str:
        """Run the agent loop for a single user input.

        Args:
            user_input: The user's request.
            on_progress: Callback for progress updates (stage, data).

        Returns:
            The final assistant response.
        """
        # Debug logging disabled for performance; re-enable via EDA_DEBUG=1 if needed
        pass
        # Add user message
        self._context_manager.add_user_message(user_input)

        # Reset cancellation flag so a previous stop doesn't block new requests
        self._cancel_event.clear()

        # Reset auto-execute counter for each new user request
        self._auto_execute_count = 0
        self._last_auto_executed_code_hash = ""

        # Lock the task description into the system prompt so the agent
        # stays on track across multiple tool-calling iterations.
        self._context_manager.set_task(user_input)

        # Inject conditional knowledge base on-demand for EDA-related requests.
        # Fine-grained injection: only relevant EDA/ckt sections are loaded
        # based on keyword matching, keeping the system prompt minimal yet
        # highly relevant to the current task.
        injected_chunks = self._ensure_knowledge_injected(user_input)
        # Fallback: if no chunks matched, inject the full API reference
        if not injected_chunks:
            self._ensure_eda_api_injected(user_input)

        final_response = ""
        tools_used: List[str] = []
        successful_tools_used: List[str] = []  # Only successful calls (for safety nets)
        tool_errors: List[str] = []

        try:
            self._task_counter += 1
            self._context_manager.set_task_number(self._task_counter)

            tools = self._select_tools(user_input)
            messages = self._context_manager.messages
            tool_round_count = 0  # How many rounds of tool calls have completed
            synthesis_violations = 0  # Times model tried to tool-call after limit
            last_turn_had_tools = False
            consecutive_empty_calls = 0  # Guard against models that loop with empty args
            # Stable ids for tool calls so streaming and execution phases share
            # the same id even if provider mutates the underlying dict.
            _tool_call_ids: Dict[int, str] = {}

            for i in range(self.max_iterations):
                self._iteration = i
                try:
                    # ── CANCELLATION CHECK ──
                    if self._cancel_event.is_set():
                        final_response = "⏹️ 操作已被用户取消。"
                        if on_progress:
                            on_progress("status", {"status": "cancelled"})
                        break

                    # ── PHASE: Determine current phase for this iteration ──
                    # After max_tool_rounds we strip tools and force synthesis,
                    # which is also the RESPONDING phase.
                    _will_force_synthesis = tool_round_count >= self.max_tool_rounds
                    if _will_force_synthesis:
                        self._set_phase(AgentPhase.RESPONDING, on_progress)
                    else:
                        self._set_phase(AgentPhase.ANALYZING, on_progress)

                    # ── BLOCKING: Ensure context budget before each LLM call ──
                    budget_err = await self._ensure_context_budget(on_progress)
                    if budget_err:
                        final_response = budget_err
                        if on_progress:
                            on_progress("status", {"status": "error", "error": budget_err})
                        break

                    if on_progress:
                        on_progress("thinking", {"iteration": i, "toolRound": tool_round_count})
                        budget = self._context_manager.get_budget_status()
                        if budget["usage_ratio"] >= 0.9:
                            on_progress("budget_warning", {
                                "usage_ratio": budget["usage_ratio"],
                                "current_tokens": budget["current_tokens"],
                                "available_tokens": budget["available_tokens"],
                            })

                    # ── FORCE THINKING BETWEEN TOOL ROUNDS ──
                    # After receiving tool results, the model tends to immediately emit
                    # the next tool_calls without any reasoning text. We inject a system
                    # nudge that forces it to analyze results first.
                    if last_turn_had_tools and i > 0:
                        think_nudge = (
                            "你刚刚收到了工具执行结果。在采取下一步行动之前，"
                            "请先用自然语言分析这些结果，说明你的理解和计划。"
                            "不要直接调用下一个工具。"
                        )
                        # Inject temporarily (non-persistent) into this turn only
                        messages = list(messages)
                        messages.append(Message(role="system", content=think_nudge))

                    # ── CONVERGENCE: Enforce max tool rounds ──
                    # After max_tool_rounds, we strip tools from the API call to force
                    # the model to synthesize and reply in natural language.
                    current_tools = self._select_tools(user_input)
                    force_synthesis = tool_round_count >= self.max_tool_rounds
                    if force_synthesis:
                        # Persist the nudge so the model sees it on EVERY subsequent turn.
                        # This is stronger than a temporary injection because it survives
                        # the messages refresh after tool results are added.
                        nudge_text = (
                            "You have reached the tool round limit. "
                            "If there is still unfinished work (files not written, commands not executed, "
                            "designs not created), you MUST mention this clearly in your reply and tell "
                            "the user exactly what remains to be done. "
                            "If the task is fully complete, provide a concise summary. "
                            "Do not mention the round limit unless the user asks."
                        )
                        # Only add once — check last message to avoid duplicates
                        last_msg = self._context_manager._messages[-1] if self._context_manager._messages else None
                        if not (last_msg and last_msg.role == "system" and last_msg.content == nudge_text):
                            self._context_manager.add_system_message(nudge_text)
                        messages = self._context_manager.messages
                        if on_progress:
                            on_progress("status", {
                                "status": "synthesis",
                                "message": f"Tool round limit ({self.max_tool_rounds}) reached — forcing natural language reply",
                            })

                    content = ""
                    tool_calls_map: Dict[int, Dict[str, Any]] = {}

                    async for chunk in self.provider.chat_completion_stream(
                        messages=messages,
                        tools=None if force_synthesis else (current_tools if current_tools else None),
                        temperature=0.2,
                    ):
                        # Check cancellation during streaming
                        if self._cancel_event.is_set():
                            if on_progress:
                                on_progress("status", {"status": "cancelled"})
                            break

                        delta = chunk.delta
                        if delta.content:
                            content += delta.content
                            # Token throttling: accumulate small chunks and flush periodically
                            # to reduce IPC overhead (each token used to be a separate JSON-RPC msg)
                            _token_buffer = getattr(self, "_token_buffer", "")
                            _token_buffer += delta.content
                            self._token_buffer = _token_buffer
                            # Flush every 30 chars or on natural breakpoints to keep UI responsive
                            if len(_token_buffer) >= 30 or delta.content.endswith((".", "!", "?", "\n", " ", ",", ";", ":", "))", "]")):
                                if on_progress:
                                    on_progress("token", {"text": _token_buffer})
                                self._token_buffer = ""
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_map:
                                    tool_calls_map[idx] = tc
                                else:
                                    existing = tool_calls_map[idx]
                                    if tc.get("id"):
                                        existing["id"] = tc["id"]
                                    if tc.get("type"):
                                        existing["type"] = tc["type"]
                                    func = tc.get("function", {})
                                    existing_func = existing.setdefault("function", {})
                                    if func.get("name"):
                                        existing_func["name"] = func["name"]
                                    if func.get("arguments"):
                                        existing_args = existing_func.get("arguments", "")
                                        new_args = func["arguments"]
                                        # Defense: skip empty containers that would wipe valid accumulated args
                                        if (isinstance(new_args, dict) and not new_args) or \
                                           (isinstance(new_args, str) and not new_args.strip()):
                                            pass  # Don't overwrite with empty dict/string
                                        elif isinstance(existing_args, dict) and isinstance(new_args, dict):
                                            existing_func["arguments"] = {**existing_args, **new_args}
                                        elif isinstance(existing_args, str) and isinstance(new_args, str):
                                            existing_func["arguments"] = existing_args + new_args
                                        else:
                                            existing_func["arguments"] = new_args

                    # Parse JSON arguments for OpenAI-style accumulated tool calls
                    tool_calls = list(tool_calls_map.values()) if tool_calls_map else None
                    if tool_calls:
                        for tc in tool_calls:
                            args = tc.get("function", {}).get("arguments", "")
                            if isinstance(args, str) and args:
                                try:
                                    tc["function"]["arguments"] = json.loads(args)
                                except json.JSONDecodeError:
                                    pass

                    # ── Synthetic thinking fallback ──
                    # If the model emitted tool_calls without any preceding content,
                    # synthesize a brief reasoning sentence so the user sees *something*
                    # before the tool card. This also gets stored in the assistant message
                    # so the model's own context history remains coherent.
                    if tool_calls and not content.strip():
                        tool_names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
                        synthetic_thinking = self._infer_tool_call_reason(tool_names)
                        content = synthetic_thinking
                        if on_progress:
                            on_progress("token", {"text": content})

                    # Flush any remaining token buffer before storing message
                    if getattr(self, "_token_buffer", ""):
                        if on_progress:
                            on_progress("token", {"text": self._token_buffer})
                        self._token_buffer = ""

                    assistant_msg = Message(
                        role="assistant",
                        content=content or None,
                        tool_calls=tool_calls,
                    )
                    self._context_manager.add_assistant_message(
                        content=assistant_msg.content,
                        tool_calls=assistant_msg.tool_calls,
                    )
                    messages = self._context_manager.messages  # Refresh after add

                    # ── HARD STOP: If force_synthesis is active but model still emitted
                    # tool_calls, we discard them and force a natural-language reply.
                    if force_synthesis and assistant_msg.tool_calls:
                        synthesis_violations += 1
                        # After 2 violations, give up and return a canned message
                        if synthesis_violations >= 2:
                            final_response = (
                                "I've gathered the available information but the model "
                                "kept attempting tool calls after the safety limit. "
                                "Here's what I found so far:\n\n"
                                f"{assistant_msg.content or '(no summary generated)' }"
                            )
                            if on_progress:
                                on_progress("status", {
                                    "status": "error",
                                    "error": "Model exceeded tool round limit twice — forcing exit",
                                })
                            break

                        # First violation: inject a synthetic "tool result" for each
                        # attempted call so the model sees why it was rejected.
                        rejection_msg = (
                            "Tool call blocked: the tool round limit has been reached. "
                            "Please reply in natural language only."
                        )
                        for tc in assistant_msg.tool_calls:
                            tool_use_id = self._normalize_tool_call_id(tc)
                            self._context_manager.add_tool_result(
                                content={"error": rejection_msg},
                                tool_call_id=tool_use_id,
                                name=tc.get("function", {}).get("name", "unknown"),
                            )
                        messages = self._context_manager.messages
                        # Don't increment tool_round_count — this was a blocked attempt
                        continue

                    # ── SAFETY NET: Auto-extract and execute code from reply ──
                    # The model often outputs complete scripts in its reply instead of
                    # calling file_write/bash. When this happens, we bypass the model
                    # entirely: extract the code, write it, and execute it automatically.
                    #
                    # NOTE: We check regardless of whether assistant_msg has tool_calls,
                    # because the model sometimes mixes code output with other tool calls
                    # (e.g., task_plan + code in the same message).
                    has_unsaved_code = self._response_contains_unsaved_code(
                        assistant_msg.content, successful_tools_used
                    )
                    if has_unsaved_code and not force_synthesis:
                        # ULTIMATE SAFETY NET: Auto-extract, write, and execute
                        auto_executed = await self._auto_execute_code_from_response(
                            assistant_msg.content, successful_tools_used, tools_used, on_progress
                        )
                        if auto_executed:
                            if on_progress:
                                on_progress("status", {
                                    "status": "correcting",
                                    "message": "Auto-extracted code from reply and executed it",
                                })
                            # Refresh messages so auto-executed tool results are visible
                            messages = self._context_manager.messages
                            # If the model also emitted tool_calls, we still execute them below.
                            # If not, we will fall through to the no-tool-calls branch.
                            pass
                        else:
                            # Fallback: inject nudge if auto-extraction failed
                            nudge = (
                                "STOP. You just output code in your reply but did NOT call "
                                "`file_write` to save it. You MUST call `file_write` with the code, "
                                "then `bash` to execute it. Do NOT reply in text — call tools now."
                            )
                            self._context_manager.add_system_message(nudge)
                            messages = self._context_manager.messages
                            if on_progress:
                                on_progress("status", {
                                    "status": "correcting",
                                    "message": "Detected unsaved code — forcing tool execution",
                                })
                            continue

                    if not assistant_msg.tool_calls:
                        self._set_phase(AgentPhase.RESPONDING, on_progress)
                        final_response = assistant_msg.content or "Done."
                        break

                    # ── PHASE: Switch to EXECUTING ──
                    self._set_phase(AgentPhase.EXECUTING, on_progress)

                    # Execute tool calls
                    if on_progress:
                        on_progress("tool_use", {
                            "count": len(assistant_msg.tool_calls),
                        })

                    # Build a human-readable reason for this round of tool calls
                    round_reason = self._infer_tool_call_reason(
                        [tc.get("function", {}).get("name", "") for tc in assistant_msg.tool_calls]
                    )

                    # Track whether any tool in this round actually executed (not validation-failed)
                    any_tool_actually_ran = False

                    # Clear per-round ID cache so each round generates fresh IDs.
                    # Enumeration index resets to 0 on each round, so stale entries
                    # from previous rounds would cause ID collisions on the frontend.
                    _tool_call_ids.clear()

                    for i, tc in enumerate(assistant_msg.tool_calls):
                        # Use the enumeration index directly — some providers (qwen via
                        # Alibaba proxy) set index=0 on every tool_call, which would
                        # cause all calls in a round to share the same ID.
                        idx = i
                        tool_use_id = _tool_call_ids.get(idx)
                        if not tool_use_id:
                            tool_use_id = self._normalize_tool_call_id(tc)
                            _tool_call_ids[idx] = tool_use_id
                        func = tc.get("function", {})
                        tool_name = func.get("name", "")
                        # Guard against None/empty arguments (some providers send null)
                        tool_args_str = func.get("arguments") or "{}"

                        try:
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                        except json.JSONDecodeError:
                            tool_args = {}

                        # Pre-validate: catch empty args for tools with required
                        # parameters BEFORE calling _execute_tool. This prevents
                        # the LLM from burning a tool round on a call it never
                        # properly constructed.
                        required_params = self._REQUIRED_PARAMS.get(tool_name, [])
                        if required_params and (not tool_args or not any(k in (tool_args or {}) for k in required_params)):
                            missing = [p for p in required_params if p not in (tool_args or {})]
                            # Auto-recovery for file_write: extract code from assistant response
                            # and fill in the arguments instead of failing.
                            if tool_name == "file_write" and assistant_msg.content:
                                import re
                                code_blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", assistant_msg.content, re.DOTALL)
                                if code_blocks:
                                    # Use the longest code block as the content
                                    best_code = max(code_blocks, key=len)
                                    # Generate a filename based on context or use a default
                                    filepath = self.context.get_temp_filepath("design.py")
                                    # Try to extract a filename from the assistant's text
                                    file_match = re.search(r'["\']([\w/.\-]+\.py)["\']', assistant_msg.content)
                                    if file_match:
                                        filepath = file_match.group(1)
                                    tool_args = {"path": filepath, "content": best_code}
                                    tool_args_str = json.dumps(tool_args)
                                    if on_progress:
                                        on_progress("status", {
                                            "status": "correcting",
                                            "message": f"Auto-filled file_write args: path={filepath}",
                                        })
                                    # Fall through to normal execution
                                    tools_used.append(tool_name)
                                    tool_result = None
                                    consecutive_empty_calls = 0
                                else:
                                    # No code blocks found — return error
                                    validation_err = (
                                        f"ERROR: file_write called with empty arguments. "
                                        f"You MUST include the script content in the 'content' parameter. "
                                        f"First write the Python script in your response, then call file_write with it."
                                    )
                                    tool_result = ToolResult(data={"error": validation_err})
                                    is_error = True
                                    consecutive_empty_calls += 1
                            else:
                                # Other tools: return clear error
                                if tool_name == "bash":
                                    hint = "You MUST call bash with 'command' (the shell command string)."
                                elif tool_name == "file_read":
                                    hint = "You MUST call file_read with 'path' (the file path to read)."
                                else:
                                    hint = f"You MUST call {tool_name} with all required parameters: {missing}."
                                validation_err = (
                                    f"ERROR: {tool_name} called with empty arguments {{}}. "
                                    f"Required parameters: {missing}. "
                                    f"{hint} "
                                    f"DO NOT call {tool_name} again without providing these parameters."
                                )
                                tool_result = ToolResult(data={"error": validation_err})
                                is_error = True
                                consecutive_empty_calls += 1
                                if consecutive_empty_calls >= 3:
                                    final_response = (
                                        f"The model repeatedly called {tool_name} without providing the required parameters {missing}. "
                                        "Please try again with a more specific request."
                                    )
                                    if on_progress:
                                        on_progress("status", {"status": "error", "error": final_response})
                                    break
                        else:
                            consecutive_empty_calls = 0
                            tools_used.append(tool_name)
                            tool_result = None  # Will be set by _execute_tool below

                        summary = self.summarize_tool_args(tool_name, tool_args, raw_args=tool_args_str)
                        base_timeout = self._get_timeout(tool_name, tool_args)
                        # Build a lightweight args preview for the UI to avoid
                        # sending multi-MB payloads over the stdout pipe.
                        _preview_args = tool_args
                        if isinstance(tool_args, dict) and "content" in tool_args:
                            content_preview = str(tool_args["content"])
                            if len(content_preview) > 500:
                                _preview_args = {k: v for k, v in tool_args.items() if k != "content"}
                                _preview_args["content"] = content_preview[:500] + " ... [truncated]"
                        if on_progress:
                            on_progress("tool_call", {
                                "name": tool_name,
                                "args": _preview_args,
                                "id": tool_use_id,
                                "iteration": self._iteration,
                                "summary": summary,
                                "reason": round_reason,
                                "toolRound": tool_round_count + 1,
                                "maxToolRounds": self.max_tool_rounds,
                                "timeout": base_timeout,
                            })
                        # Debug write removed for performance

                        if tool_result is None:
                            _tool_start_ts = asyncio.get_event_loop().time()
                            tool_result = await self._execute_tool(tool_name, tool_args, tool_use_id, on_progress)
                            _tool_duration_ms = int((asyncio.get_event_loop().time() - _tool_start_ts) * 1000)
                        else:
                            # Pre-validation already produced an error result
                            _tool_duration_ms = 0

                        # Collect errors for summary
                        is_error = isinstance(tool_result.data, dict) and tool_result.data.get("error")
                        if is_error:
                            err = tool_result.data["error"]
                            if not any(e in err for e in tool_errors):
                                tool_errors.append(err)
                            # If this was a pure validation failure, the tool never actually ran.
                            # Empty-args tracking and bail-out is now handled by pre-validation
                            # above, so we only reset here for non-validation failures.
                            if "Validation failed" not in err and "Permission denied" not in err:
                                any_tool_actually_ran = True
                                if tool_name not in successful_tools_used:
                                    successful_tools_used.append(tool_name)
                        else:
                            any_tool_actually_ran = True
                            consecutive_empty_calls = 0
                            if tool_name not in successful_tools_used:
                                successful_tools_used.append(tool_name)

                        # Notify frontend that this tool call is complete
                        _preview_result = tool_result.data
                        if isinstance(_preview_result, dict):
                            _preview_result = dict(_preview_result)
                            for k in ("stdout", "stderr", "content", "output"):
                                if k in _preview_result and isinstance(_preview_result[k], str) and len(_preview_result[k]) > 2000:
                                    _preview_result[k] = _preview_result[k][:2000] + " ... [truncated]"
                        if on_progress:
                            on_progress("tool_complete", {
                                "name": tool_name,
                                "result": _preview_result,
                                "tool_call_id": tool_use_id,
                                "iteration": self._iteration,
                                "is_error": bool(is_error),
                                "duration_ms": _tool_duration_ms,
                            })

                        # Add tool result to messages
                        self._context_manager.add_tool_result(
                            content=tool_result.data,
                            tool_call_id=tool_use_id,
                            name=tool_name,
                        )
                        messages = self._context_manager.messages  # Refresh after add

                        # Update plan progress if there's an active plan
                        self._maybe_update_plan(tool_name, on_progress)

                    # Only count this as a tool round if at least one tool actually ran.
                    # Validation failures (e.g. empty bash command) don't count — they
                    # would otherwise waste a round and push us toward the limit.
                    if any_tool_actually_ran:
                        tool_round_count += 1
                        last_turn_had_tools = True
                    else:
                        # All tools in this round were validation failures.
                        # Inject a nudge so the model sees why and fixes params next turn.
                        nudge = (
                            "Your previous tool call(s) failed validation and did NOT execute. "
                            "This does NOT count as a tool round. "
                            "Review the error messages above, fix the parameters, and retry."
                        )
                        self._context_manager.add_system_message(nudge)
                        messages = self._context_manager.messages
                        last_turn_had_tools = True

                except Exception as e:
                    import traceback
                    err_msg = f"Internal error in iteration {i}: {type(e).__name__}: {e}"
                    traceback_str = traceback.format_exc()
                    # Error logging to stderr disabled for performance; use EDA_DEBUG=1 to re-enable
                    if on_progress:
                        try:
                            on_progress("status", {"status": "error", "error": err_msg})
                            on_progress("token", {"text": f"\n\n⚠️ {err_msg}\n"})
                        except Exception as progress_err:
                            # Error write removed for performance; use EDA_DEBUG=1 to re-enable
                            pass
                    # Inject the error into context so the model can recover
                    self._context_manager.add_system_message(
                        f"CRITICAL INTERNAL ERROR: {err_msg}. Please retry with a simpler request."
                    )
                    messages = self._context_manager.messages
                    continue

            else:
                final_response = "Max iterations reached. Please refine your request."
                if on_progress:
                    on_progress("thinking_stop", {})
                    on_progress("phase", {"phase": "responding"})
        finally:
            # Clear task lock when the agent run completes (success or failure)
            self._context_manager.clear_task()
            # Clean up the context snapshot file for this task
            self._context_manager.clear_task_snapshot()

        # Generate task summary if EDA tools were involved
        summary = self._generate_task_summary(tools_used, tool_errors, final_response)
        if summary:
            return f"{final_response}\n\n---\n\n{summary}"
        return final_response

    # Default timeouts per tool category (seconds)
    _TOOL_TIMEOUTS: Dict[str, int] = {
        # File operations
        "file_read": 10,
        "file_write": 60,   # Large files may take longer
        "file_edit": 10,
        "glob": 10,
        "grep": 10,
        "diff": 10,
        # Shell commands — moderate
        "bash": 30,
        # EDA tools
        "design_open": 15,
        "design_save": 10,
        "design_close": 10,
        "design_query": 10,
        "schematic_edit": 15,
        "layout_edit": 15,
        "task_plan": 10,
        "set_todo_list": 5,
        "background_submit": 15,
        "background_status": 10,
        "background_results": 10,
        # Simulation / verification — long running
        "simulation_run": 600,
        "drc_run": 600,
        "lvs_run": 600,
        "pex_run": 600,
        "circuit_harness": 300,
        "emir_run": 600,
    }
    _DEFAULT_TIMEOUT: int = 15

    @staticmethod
    def _infer_tool_call_reason(tool_names: List[str]) -> str:
        """Generate a short human-readable reason for why these tools are being called.

        This helps users understand the agent's intent without reading raw args.
        """
        if not tool_names:
            return "Processing..."

        primary = tool_names[0]
        names = set(tool_names)

        if "task_plan" in names:
            return "Generating a design plan based on your request..."
        if "design_open" in names:
            return "Opening the design database to begin editing..."
        if "design_save" in names:
            return "Saving the current design state..."
        if "design_query" in names:
            return "Querying the current design state..."
        if "schematic_edit" in names:
            return "Editing the schematic..."
        if "layout_edit" in names:
            return "Editing the layout..."
        if "set_todo_list" in names:
            return "Updating the task todo list..."
        if "background_submit" in names:
            return "Submitting a long-running task to the background..."
        if "background_status" in names or "background_results" in names:
            return "Checking background task status..."
        if names <= {"file_read", "file_write", "file_edit", "glob", "grep", "diff"}:
            return "Reading or modifying project files..."
        if "bash" in names and len(names) == 1:
            # Summary already shows the actual command; generic reason is redundant.
            return ""
        if len(names) > 1:
            return f"Executing multiple steps ({', '.join(list(names)[:3])}{'...' if len(names) > 3 else ''})..."
        return f"Running {primary}..."

    def _generate_task_summary(self, tools_used: List[str], tool_errors: List[str], final_response: str) -> str:
        """Generate a summary when EDA design tasks complete.

        Returns a markdown-formatted summary of the design state, including
        design location, simulation results, task progress, and failure analysis.
        """
        ctx = self.context
        eda_tools = {
            "design_open", "design_save", "design_close", "design_query",
            "schematic_edit", "layout_edit",
            "task_plan", "set_todo_list",
        }
        used_eda = [t for t in tools_used if t in eda_tools]
        if not used_eda:
            return ""

        lines: List[str] = []

        # Determine success: no errors and design is open
        has_errors = len(tool_errors) > 0
        design_open = ctx.active_design is not None

        if not has_errors and design_open:
            lines.append("## ✅ 设计任务完成")
            lines.append("")
            lines.append("**设计位置**:")
            lines.append(f"- Library: `{ctx.active_lib or 'N/A'}`")
            lines.append(f"- Cell: `{ctx.active_cell or 'N/A'}`")
            lines.append(f"- View: `{ctx.active_view or 'N/A'}`")
            lines.append(f"- 项目目录: `{ctx.project_root}`")

            if ctx.last_sim_result:
                lines.append("")
                lines.append("**仿真结果摘要**:")
                if isinstance(ctx.last_sim_result, dict):
                    for k, v in ctx.last_sim_result.items():
                        if k in ("error", "traceback"):
                            continue
                        v_str = str(v)[:100] + ("..." if len(str(v)) > 100 else "")
                        lines.append(f"- {k}: `{v_str}`")
                else:
                    lines.append(f"- {str(ctx.last_sim_result)[:200]}")

            if ctx.todo_list:
                done = sum(1 for t in ctx.todo_list if t.get("status") == "done")
                total = len(ctx.todo_list)
                lines.append("")
                lines.append(f"**任务进度**: {done}/{total} 完成")
                if done < total:
                    pending = [t["item"] for t in ctx.todo_list if t.get("status") != "done"]
                    lines.append(f"**待完成**: {', '.join(pending[:3])}" + ("..." if len(pending) > 3 else ""))

        elif has_errors:
            lines.append("## ⚠️ 任务未完全完成")
            lines.append("")
            lines.append("**遇到的问题**:")
            for err in tool_errors[:3]:
                err_short = err[:150] + ("..." if len(err) > 150 else "")
                lines.append(f"- {err_short}")

            lines.append("")
            lines.append("**建议**:")
            # Provide targeted advice based on error content
            error_text = " ".join(tool_errors).lower()
            if "permission" in error_text:
                lines.append("- 某些操作需要用户授权，请点击弹窗中的「同意」后继续。")
            elif "timeout" in error_text:
                lines.append("- 操作超时，建议使用 `background_submit` 将长时间任务放入后台执行。")
            elif "not found" in error_text or "no such" in error_text:
                lines.append("- 文件或器件未找到，请检查路径、库名或单元名是否正确。")
            elif "pyaether" in error_text or "not available" in error_text:
                lines.append("- EDA SDK 环境未就绪，请确认 EDA 环境已正确安装和配置。")
            elif "drc" in error_text or "lvs" in error_text:
                lines.append("- DRC/LVS 验证失败，请检查版图设计规则或原理图-版图一致性。")
            elif "simulation" in error_text or "convergence" in error_text:
                lines.append("- 仿真未收敛，请检查偏置点、初始条件或减小仿真步长。")
            else:
                lines.append("- 检查设计参数、仿真设置或 PDK 配置，然后重试。")
                lines.append("- 如需详细排查，可使用 `file_read` 查看日志文件。")

            if ctx.active_design:
                lines.append("")
                lines.append("**当前设计状态**:")
                lines.append(f"- Library: `{ctx.active_lib or 'N/A'}`")
                lines.append(f"- Cell: `{ctx.active_cell or 'N/A'}`")
                lines.append(f"- View: `{ctx.active_view or 'N/A'}`")

        else:
            # EDA tools used but no design opened and no errors (exploration phase)
            lines.append("## 📝 任务执行摘要")
            lines.append("")
            lines.append(f"**执行的工具**: {', '.join(set(used_eda))}")
            lines.append(f"**项目目录**: `{ctx.project_root}`")
            if ctx.todo_list:
                done = sum(1 for t in ctx.todo_list if t.get("status") == "done")
                total = len(ctx.todo_list)
                lines.append(f"**任务进度**: {done}/{total} 完成")

        return "\n".join(lines)

    def _get_timeout(self, name: str, args: Dict[str, Any]) -> int:
        """Determine timeout based on tool name and argument complexity."""
        base = self._TOOL_TIMEOUTS.get(name, self._DEFAULT_TIMEOUT)

        # User override takes highest priority
        user_timeout = args.get("timeout")
        if isinstance(user_timeout, (int, float)) and user_timeout > 0:
            # Bash tool schema defines timeout in milliseconds; convert to seconds
            if name == "bash":
                return int(user_timeout / 1000)
            return int(user_timeout)

        # Bash: cap at 120s max (2 minutes is plenty for filesystem ops)
        if name == "bash":
            return min(base, 120)

        return base

    def _is_path_outside_project(self, path: str) -> bool:
        """Check if a path goes outside the project root."""
        if not path:
            return False
        try:
            project_root = os.path.abspath(getattr(self.context, "project_root", os.getcwd()))
            target = os.path.abspath(os.path.join(project_root, path))
            return not target.startswith(project_root + os.sep) and target != project_root
        except Exception:
            return False

    def _check_tool_permissions(self, name: str, args: Dict[str, Any]) -> Optional[ToolResult]:
        """Check if the tool execution requires user approval.

        Returns None if allowed, or a ToolResult with permission request if denied.
        """
        ctx = self.context

        # Session-level approval bypasses all remaining checks
        if ctx.session_approved:
            return None

        # EDA tools: any operation on the EDA database needs approval
        eda_tools = {
            "design_open", "design_save", "design_close", "design_query", "design_delete",
            "schematic_edit", "layout_edit",
        }
        if name in eda_tools and not ctx.eda_access_approved:
            return ToolResult(data={
                "error": f"EDA operation '{name}' requires user approval before modifying the design database.",
                "needsPermission": True,
                "permissionType": "eda_access",
                "tool": name,
            })

        # File tools: check if path goes outside project_root
        file_tools = {"file_read", "file_write", "file_edit", "glob", "grep"}
        if name in file_tools and not ctx.file_access_approved:
            path = args.get("path") or args.get("file_path") or args.get("pattern") or ""
            if self._is_path_outside_project(path):
                return ToolResult(data={
                    "error": f"File operation on '{path}' goes outside the project directory and requires approval.",
                    "needsPermission": True,
                    "permissionType": "file_access",
                    "tool": name,
                    "path": path,
                })

        # Bash: check if command targets paths outside project
        if name == "bash" and not ctx.file_access_approved:
            cmd = args.get("command", "")
            # Simple heuristic: check for absolute paths or ../ patterns
            import re
            suspicious_paths = re.findall(r'(?:[\s;|&]|^)(/[^\s\;\|\&\`\'\"]+|\.\./[^\s\;\|\&\`\'\"]+)', cmd)
            for p in suspicious_paths:
                if self._is_path_outside_project(p):
                    return ToolResult(data={
                        "error": f"Shell command references path outside project directory: {p}",
                        "needsPermission": True,
                        "permissionType": "file_access",
                        "tool": name,
                        "path": p,
                    })

        return None

    def _track_tool_action(self, name: str, args: Dict[str, Any], result: ToolResult) -> None:
        """Record a recent action for the design state panel."""
        action = name
        if "lib" in args:
            action += f" lib={args['lib']}"
        if "cell" in args:
            action += f" cell={args['cell']}"
        if "view" in args:
            action += f" view={args['view']}"
        if "command" in args:
            action += f" cmd={args['command'][:30]}"
        if "simulator" in args:
            action += f" sim={args['simulator']}"
        success = not (isinstance(result.data, dict) and result.data.get("error"))
        action += " ✓" if success else " ✕"
        self.context.recent_actions.append(action)
        # Keep last 20 actions
        if len(self.context.recent_actions) > 20:
            self.context.recent_actions = self.context.recent_actions[-20:]

    def _build_design_state(self) -> Dict[str, Any]:
        """Build the current design state payload for the UI."""
        ctx = self.context
        return {
            "activeLib": ctx.active_lib,
            "activeCell": ctx.active_cell,
            "activeView": ctx.active_view,
            "activeDesign": getattr(ctx.active_design, "name", None) if ctx.active_design else None,
            "todoList": ctx.todo_list,
            "recentActions": ctx.recent_actions[-10:],
        }

    def _validate_tool_result(self, name: str, args: Dict[str, Any], result: ToolResult) -> Tuple[bool, str]:
        """Validate that a tool result is semantically correct.

        Returns (is_valid, message). If is_valid is False, message explains why.
        """
        data = result.data

        # 1. Generic: if result itself reports an error, it's already invalid
        if isinstance(data, dict) and data.get("error"):
            return False, data["error"]

        # 2. Tool-specific validations
        if name == "design_open":
            # After opening, the context should have an active design
            if not self.context.active_design:
                return False, "design_open reported success but no active design is set in context"

        elif name == "file_read":
            content = data if isinstance(data, str) else (data.get("content") if isinstance(data, dict) else "")
            if not content or not content.strip():
                return False, "file_read returned empty content"

        elif name == "bash":
            if isinstance(data, dict):
                stderr = data.get("stderr", "")
                returncode = data.get("returncode", 0)
                if returncode != 0:
                    return False, f"bash command exited with code {returncode}: {stderr[:200]}"
                # Warn on stderr but don't fail (many tools write warnings to stderr)
                if stderr and any(kw in stderr.lower() for kw in ["error", "fatal", "exception", "traceback"]):
                    return False, f"bash command produced error output: {stderr[:200]}"

        elif name in ("schematic_edit", "layout_edit"):
            # EDA edits should return a dict with status info; absence of 'error' is good,
            # but we also check that something was actually created/modified.
            if isinstance(data, dict):
                if data.get("items_created") == 0 and data.get("items_modified") == 0:
                    # Not necessarily an error — could be a no-op query
                    pass

        elif name == "task_plan":
            # Plan must have phases
            if isinstance(data, dict) and not data.get("phases"):
                return False, "task_plan returned an empty plan with no phases"

        return True, ""

    def _analyze_timeout(self, name: str, args: Dict[str, Any], timeout: int) -> str:
        """Analyze why a tool timed out and provide actionable advice."""
        if name in ("design_open", "schematic_edit", "layout_edit"):
            return (
                f"EDA operation '{name}' timed out after {timeout}s. "
                "Possible causes: large design loading slowly, database lock, or EDA SDK not responding. "
                "Try closing other designs first or restarting the EDA environment."
            )
        elif name == "bash":
            cmd = args.get("command", "")
            return (
                f"Shell command timed out after {timeout}s: `{cmd[:80]}...`. "
                "Possible causes: command waiting for input, infinite loop, or heavy I/O. "
                "Try running with explicit timeout or check if the command is interactive."
            )
        elif name in ("file_read", "file_write", "file_edit"):
            path = args.get("path", "")
            return (
                f"File operation on '{path}' timed out after {timeout}s. "
                "Possible causes: file is extremely large, network filesystem lag, or permission issues. "
                "Try reading in smaller chunks or check file size."
            )
        elif name == "glob" or name == "grep":
            return (
                f"Search operation timed out after {timeout}s. "
                "Possible causes: searching a very large directory tree or binary files. "
                "Try narrowing the pattern or excluding large directories."
            )
        else:
            return (
                f"Operation timed out after {timeout}s. "
                "Possible causes: slow system response, resource contention, or the operation is inherently long-running. "
                "Consider breaking the task into smaller steps."
            )

    async def _execute_tool(
        self,
        name: str,
        args: Dict[str, Any],
        tool_use_id: str,
        on_progress: Optional[Callable[[str, Any], None]] = None,
        max_retries: int = 2,
    ) -> ToolResult:
        """Execute a single tool by name with automatic timeout and retry.

        Handles timeout with exponential backoff and post-execution validation.
        """
        tool = self.registry.get(name)
        if tool is None:
            available = ", ".join(self.registry.list_tool_names())
            return ToolResult(data={
                "error": (
                    f"Validation failed: Tool '{name}' does not exist. "
                    f"Available tools: {available}. "
                    f"NEVER invent tool names. Use only the registered tools."
                ),
            })

        # Check user permissions before execution
        perm_result = self._check_tool_permissions(name, args)
        if perm_result is not None:
            return perm_result

        base_timeout = self._get_timeout(name, args)
        last_error: Optional[str] = None

        # Progress callback adapter
        def progress_adapter(p: ToolProgress) -> None:
            if on_progress:
                on_progress("tool_progress", {"tool": name, "data": p.data, "iteration": self._iteration})

        for attempt in range(max_retries + 1):
            timeout = int(base_timeout * (1.5 ** attempt))
            try:
                # Validate input (only on first attempt; args may change on retry)
                if attempt == 0:
                    validation = tool.validate_input(args, self.context)
                    if not validation.result:
                        return ToolResult(data={
                            "error": f"Validation failed: {validation.message}",
                        })

                    # Check tool-level permissions
                    perm = tool.check_permissions(args, self.context)
                    if perm.behavior == "deny":
                        return ToolResult(data={"error": f"Permission denied: {perm.message}"})
                    if perm.updated_input:
                        args = perm.updated_input

                if attempt > 0 and on_progress:
                    on_progress("tool_progress", {
                        "tool": name,
                        "data": {
                            "stage": "retry",
                            "message": f"Retrying ({attempt}/{max_retries}) with timeout {timeout}s...",
                            "attempt": attempt,
                            "max_retries": max_retries,
                        },
                        "iteration": self._iteration,
                    })

                # EDA tools wrap synchronous SDK C-extension calls.
                # Run them in a thread pool so asyncio.wait_for can actually
                # enforce the timeout and the main loop stays responsive (e.g. ping).
                if isinstance(tool, EDATool):
                    loop = asyncio.get_running_loop()

                    def _run_eda_in_thread():
                        # EDA tools call synchronous SDK C-extensions.
                        # We need a fresh event loop inside the worker thread.
                        thread_loop = asyncio.new_event_loop()
                        try:
                            return thread_loop.run_until_complete(
                                tool.call(args, self.context, progress_adapter)
                            )
                        finally:
                            thread_loop.close()

                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, _run_eda_in_thread),
                        timeout=timeout,
                    )
                else:
                    result = await asyncio.wait_for(
                        tool.call(args, self.context, progress_adapter),
                        timeout=timeout,
                    )

                # ── Post-execution validation ──
                is_valid, validation_msg = self._validate_tool_result(name, args, result)
                if not is_valid:
                    return ToolResult(data={
                        "error": f"Tool '{name}' executed but validation failed: {validation_msg}",
                        "raw_result": result.data,
                    })

                # Track action and emit design state update for EDA tools
                self._track_tool_action(name, args, result)
                if on_progress and isinstance(tool, EDATool):
                    on_progress("design_state", self._build_design_state())

                # Annotate result with retry metadata for transparency
                if attempt > 0:
                    if isinstance(result.data, dict):
                        result.data["_retry_count"] = attempt
                return result

            except asyncio.TimeoutError:
                last_error = (
                    f"Attempt {attempt + 1}/{max_retries + 1}: "
                    f"Tool '{name}' timed out after {timeout}s."
                )
                # Analyze why it timed out for better error messages
                analysis = self._analyze_timeout(name, args, timeout)
                last_error += f"\nAnalysis: {analysis}"

                if attempt < max_retries:
                    # Backoff before retry
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    # All retries exhausted
                    return ToolResult(data={
                        "error": last_error,
                        "timed_out": True,
                        "suggestion": "The operation consistently timed out. Try a simpler request, check system resources, or run as a background task.",
                    })

            except Exception as e:
                # Non-timeout errors are NOT retried (they are deterministic)
                return ToolResult(data={"error": str(e)})

        # Should never reach here
        return ToolResult(data={"error": last_error or "Unknown execution error"})
