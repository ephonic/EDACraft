"""
rtlgen.verilog_import — Verilog → rtlgen Python API 转换器

将 Verilog RTL 代码库按原有层次结构转换为 rtlgen Python API 代码。

用法:
    importer = VerilogImporter("path/to/verilog/repo")
    importer.scan_repo()
    importer.emit_repo("path/to/output")

依赖: pyverilog
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from pyverilog.vparser.parser import VerilogParser
    from pyverilog.vparser import ast as vast
except ImportError as _e:
    raise ImportError(
        "pyverilog is required for verilog_import. Install it via: pip install pyverilog"
    ) from _e


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class VerilogImporter:
    """扫描 Verilog 代码库并生成对应的 rtlgen Python 代码。"""

    def __init__(self, top_dir: str):
        self.top_dir = Path(top_dir).resolve()
        self.modules: Dict[str, vast.ModuleDef] = {}
        self.module_files: Dict[str, Path] = {}
        self._parser = VerilogParser()

    def scan_repo(self, include_dirs: Optional[List[str]] = None) -> None:
        """递归扫描目录下的所有 .v / .sv 文件并解析模块。

        Args:
            include_dirs: 额外的 `include 搜索路径列表。
        """
        if include_dirs is None:
            include_dirs = [str(self.top_dir)]
        for ext in ("*.v", "*.sv", "*.vhd"):
            for path in self.top_dir.rglob(ext):
                self.parse_file(path, include_dirs=include_dirs)

    def _preprocess_text(self, text: str, include_dirs: Optional[List[str]] = None) -> str:
        """文本级预处理：修复 pyverilog 不兼容的语法。"""
        import re
        # 1. Windows CRLF → Unix LF
        text = text.replace("\r\n", "\n")
        # 2. SystemVerilog for-loop inline integer declaration → traditional
        #    for (integer j = 255; ...) → for (j = 255; ...)
        #    (pyverilog cannot parse integer inside always blocks)
        pattern = r'\bfor\s*\(\s*integer\s+([a-zA-Z_]\w*)\s*=\s*([^;]+);\s*([^;]+);\s*([^)]+)\)'
        def repl(m):
            var, init, cond, update = m.groups()
            return f"for ({var} = {init}; {cond}; {update})"
        text = re.sub(pattern, repl, text)
        # 3. Remove standalone integer declarations inside always/initial blocks
        #    (they were extracted by step 2 or appear standalone in SV)
        text = re.sub(r'\binteger\s+[a-zA-Z_]\w*\s*;', '', text)
        # 4. SystemVerilog unsized constants → Verilog-2001 sized constants
        #    'd10 → 32'd10,  '0 → 1'b0,  '1 → 1'b1
        text = re.sub(r"(?<![0-9a-zA-Z_])'(d[0-9]+)", r"32'\1", text)
        text = re.sub(r"(?<![0-9a-zA-Z_])'0\b", r"1'b0", text)
        text = re.sub(r"(?<![0-9a-zA-Z_])'1\b", r"1'b1", text)
        # 5. C-style increment/decrement → Verilog
        #    i++ → i = i + 1,  i-- → i = i - 1
        text = re.sub(r'\b([a-zA-Z_]\w*)\+\+', r'\1 = \1 + 1', text)
        text = re.sub(r'\b([a-zA-Z_]\w*)--', r'\1 = \1 - 1', text)
        return text

    def _iverilog_preprocess(self, path: Path, include_dirs: Optional[List[str]] = None) -> Optional[str]:
        """使用 iverilog 预处理 include/define/ifdef。返回预处理后的文本或 None。"""
        import subprocess, tempfile, os
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.v', delete=False, encoding='utf-8') as f:
                f.write(path.read_text(encoding='utf-8', errors='ignore'))
                tmp_in = f.name
            with tempfile.NamedTemporaryFile(mode='w', suffix='.v', delete=False, encoding='utf-8') as f:
                tmp_out = f.name

            cmd = ["iverilog", "-E", "-g2005-sv", "-o", tmp_out]
            if include_dirs:
                for d in include_dirs:
                    cmd.extend(["-I", d])
            # 添加文件所在目录到 include 路径
            cmd.extend(["-I", str(path.parent)])
            cmd.append(tmp_in)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                # iverilog 预处理失败（可能是语法错误），回退到直接读取
                os.unlink(tmp_in)
                os.unlink(tmp_out)
                return None

            text = Path(tmp_out).read_text(encoding="utf-8", errors="ignore")
            os.unlink(tmp_in)
            os.unlink(tmp_out)
            return text
        except FileNotFoundError:
            # iverilog 未安装
            return None
        except Exception:
            return None

    def parse_file(self, path: Path, include_dirs: Optional[List[str]] = None) -> None:
        """解析单个 Verilog 文件，提取其中的 module 定义。"""
        text = path.read_text(encoding="utf-8", errors="ignore")

        # 尝试 iverilog 预处理（处理 include/define/ifdef）
        preprocessed = self._iverilog_preprocess(path, include_dirs)
        if preprocessed is not None:
            text = preprocessed

        # 文本级预处理（修复 pyverilog 不兼容语法）
        text = self._preprocess_text(text, include_dirs)

        # pyverilog 解析器可能因单个文件错误而失败，try/except 隔离
        try:
            ast = self._parser.parse(text)
        except Exception as e:
            # 简单跳过有语法错误的文件，记录警告
            print(f"[verilog_import] Warning: failed to parse {path}: {e}")
            return

        for item in ast.description.definitions:
            if isinstance(item, vast.ModuleDef):
                name = item.name
                self.modules[name] = item
                self.module_files[name] = path.resolve()

    def emit_module(self, module_name: str) -> str:
        """生成单个模块的 Python 代码。"""
        mod_ast = self.modules[module_name]
        emitter = _ModuleEmitter(mod_ast, self)
        return emitter.emit()

    def emit_repo(self, output_dir: str, package_name: str = "rtl_imported") -> None:
        """生成整个代码库的 Python 代码，保持目录结构。

        Args:
            output_dir: 输出根目录
            package_name: 生成的 Python 包名
        """
        out_root = Path(output_dir) / package_name
        out_root.mkdir(parents=True, exist_ok=True)

        # 按文件分组模块，保持目录结构
        file_to_modules: Dict[Path, List[str]] = {}
        for name, file_path in self.module_files.items():
            rel = file_path.relative_to(self.top_dir)
            file_to_modules.setdefault(rel, []).append(name)

        # 生成 __init__.py
        (out_root / "__init__.py").write_text("", encoding="utf-8")

        for rel_path, mod_names in file_to_modules.items():
            # 将 .v -> .py，保持目录结构
            py_rel = rel_path.with_suffix(".py")
            py_path = out_root / py_rel
            py_path.parent.mkdir(parents=True, exist_ok=True)

            parts = []
            parts.append("\"\"\"Auto-generated from Verilog by rtlgen.verilog_import.\"\"\"")
            parts.append("from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam")
            parts.append("from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen")
            parts.append("")

            for mod_name in mod_names:
                parts.append(self.emit_module(mod_name))
                parts.append("")

            py_path.write_text("\n".join(parts), encoding="utf-8")

        # 生成汇总 __init__.py
        all_names = list(self.modules.keys())
        init_path = out_root / "__init__.py"
        init_lines = ["\"\"\"Auto-generated rtlgen package.\"\"\""]
        for rel_path in file_to_modules:
            module_py = ".".join(rel_path.with_suffix("").parts)
            init_lines.append(f"from .{module_py} import *")
        init_lines.append("")
        init_lines.append(f"__all__ = {all_names!r}")
        init_path.write_text("\n".join(init_lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Module-level emitter
# ---------------------------------------------------------------------------

class _ModuleEmitter:
    """将单个 pyverilog ModuleDef AST 转换为 rtlgen Python 代码。"""

    # Verilog 操作符 → Python 操作符映射
    _BINOP_MAP = {
        "Plus": "+",
        "Minus": "-",
        "Times": "*",
        "Divide": "//",
        "Mod": "%",
        "Power": "**",
        "Sll": "<<",
        "Srl": ">>",
        "Sra": ">>>",
        "Sla": "<<<",
        "And": "&",
        "Or": "|",
        "Xor": "^",
        "Xnor": "^~",
        "Land": "&",
        "Lor": "|",
        "LessThan": "<",
        "GreaterThan": ">",
        "LessEq": "<=",
        "GreaterEq": ">=",
        "Eq": "==",
        "NotEq": "!=",
        "Eql": "===",
        "NotEql": "!==",
    }

    _UNARYOP_MAP = {
        "Uplus": "+",
        "Uminus": "-",
        "Ulnot": "~",
        "Unot": "not ",
        "Uand": "&",
        "Unand": "~&",
        "Uor": "|",
        "Unor": "~|",
        "Uxor": "^",
        "Uxnor": "^~",
    }

    def __init__(self, module_ast: vast.ModuleDef, importer: VerilogImporter):
        self.ast = module_ast
        self.importer = importer
        self.lines: List[str] = []
        self.indent_level = 0
        self._port_names: Set[str] = set()
        self._sig_names: Set[str] = set()
        self._mem_names: Set[str] = set()
        self._arr_names: Set[str] = set()
        self._param_names: Set[str] = set()
        self._localparam_names: Set[str] = set()
        self._inside_comb = False
        self._inside_seq = False
        self._inside_for = False
        self._local_vars: Set[str] = set()
        self._always_clock: Optional[str] = None
        self._always_reset: Optional[str] = None
        self._reset_async = False
        self._reset_active_low = False

    @property
    def _ind(self) -> str:
        return "    " * self.indent_level

    def emit(self) -> str:
        self.lines = []
        self._collect_signals()
        self._emit_class_header()
        self._emit_params()
        self._emit_ports()
        self._emit_internal_signals()
        self._emit_body()
        self._emit_class_footer()
        return "\n".join(self.lines)

    # -----------------------------------------------------------------
    # Pre-scan: collect signal names for classification
    # -----------------------------------------------------------------
    def _collect_signals(self):
        """预扫描 AST，分类所有信号。"""
        for item in self.ast.items:
            self._scan_item(item)

    def _scan_item(self, item: Any):
        if isinstance(item, vast.Decl):
            for decl in item.list:
                self._scan_decl(decl)
        elif isinstance(item, (vast.Input, vast.Output, vast.Inout)):
            self._port_names.add(item.name)
        elif isinstance(item, (vast.Wire, vast.Reg, vast.Integer)):
            self._sig_names.add(item.name)
        elif isinstance(item, vast.Parameter):
            self._param_names.add(item.name)
        elif isinstance(item, vast.Localparam):
            self._localparam_names.add(item.name)
        elif isinstance(item, vast.Always):
            for stmt in item.statement.statements if hasattr(item.statement, "statements") else [item.statement]:
                self._scan_stmt_for_mem(stmt)
        elif isinstance(item, vast.GenerateStatement):
            for stmt in item.items:
                self._scan_item(stmt)

    def _scan_decl(self, decl: Any):
        if isinstance(decl, (vast.Input, vast.Output, vast.Inout)):
            self._port_names.add(decl.name)
        elif isinstance(decl, (vast.Wire, vast.Reg, vast.Integer)):
            self._sig_names.add(decl.name)
        elif isinstance(decl, vast.Parameter):
            self._param_names.add(decl.name)
        elif isinstance(decl, vast.Localparam):
            self._localparam_names.add(decl.name)
        elif isinstance(decl, vast.Genvar):
            pass

    def _scan_stmt_for_mem(self, stmt: Any):
        """扫描语句，将带有 Dimensions 且在 always 中读写的 reg 标记为 Memory。"""
        if isinstance(stmt, vast.BlockingSubstitution) or isinstance(stmt, vast.NonblockingSubstitution):
            self._mark_lvalue_as_mem(stmt.left)
        elif isinstance(stmt, vast.IfStatement):
            for s in stmt.true_statement.statements if hasattr(stmt.true_statement, "statements") else [stmt.true_statement]:
                self._scan_stmt_for_mem(s)
            if stmt.false_statement:
                for s in stmt.false_statement.statements if hasattr(stmt.false_statement, "statements") else [stmt.false_statement]:
                    self._scan_stmt_for_mem(s)
        elif isinstance(stmt, vast.CaseStatement):
            for case in stmt.caselist:
                for s in case.statement.statements if hasattr(case.statement, "statements") else [case.statement]:
                    self._scan_stmt_for_mem(s)
        elif isinstance(stmt, vast.ForStatement):
            for s in stmt.statement.statements if hasattr(stmt.statement, "statements") else [stmt.statement]:
                self._scan_stmt_for_mem(s)

    def _mark_lvalue_as_mem(self, node: Any):
        """如果 lvalue 是带维度的标识符，标记为 memory。"""
        if isinstance(node, vast.Pointer):
            if isinstance(node.var, vast.Identifier):
                name = node.var.name
                if name in self._sig_names:
                    self._sig_names.discard(name)
                    self._mem_names.add(name)
        elif isinstance(node, vast.Partselect):
            if isinstance(node.var, vast.Identifier):
                name = node.var.name
                if name in self._sig_names:
                    self._sig_names.discard(name)
                    self._arr_names.add(name)

    # -----------------------------------------------------------------
    # Class header
    # -----------------------------------------------------------------
    def _emit_class_header(self):
        self.lines.append(f"class {self.ast.name}(Module):")
        self.lines.append(f'    def __init__(self, name: str = "{self.ast.name}")')
        # 收集参数列表
        params = []
        for item in self.ast.items:
            if isinstance(item, vast.Decl):
                for decl in item.list:
                    if isinstance(decl, vast.Parameter):
                        params.append(decl)
        if params:
            param_strs = [f"{p.name}: int = {self._param_default(p)}" for p in params]
            self.lines[-1] += ", " + ", ".join(param_strs)
        self.lines[-1] += ":"
        self.lines.append(f'        super().__init__(name or "{self.ast.name}")')
        self.lines.append("")
        self.indent_level = 2

    def _param_default(self, p: vast.Parameter) -> str:
        if hasattr(p, "value") and p.value is not None:
            return self._emit_expr(p.value)
        return "0"

    # -----------------------------------------------------------------
    # Parameters
    # -----------------------------------------------------------------
    def _emit_params(self):
        # Paramlist
        if self.ast.paramlist:
            for item in self.ast.paramlist.params:
                if isinstance(item, vast.Decl):
                    for decl in item.list:
                        if isinstance(decl, vast.Parameter):
                            default = self._param_default(decl)
                            self.lines.append(f"{self._ind}self.add_param(\"{decl.name}\", {default})")
                elif isinstance(item, vast.Parameter):
                    default = self._param_default(item)
                    self.lines.append(f"{self._ind}self.add_param(\"{item.name}\", {default})")
        # Localparams in items
        for item in self.ast.items:
            if isinstance(item, vast.Decl):
                for decl in item.list:
                    if isinstance(decl, vast.Localparam):
                        default = self._param_default(decl)
                        self.lines.append(f"{self._ind}self.add_localparam(\"{decl.name}\", {default})")
        # 记录 parameter/localparam 以便后续引用

    # -----------------------------------------------------------------
    # Ports
    # -----------------------------------------------------------------
    def _emit_ports(self):
        port_items = []
        port_names = set()
        # Portlist 是 ModuleDef 的单独属性
        if self.ast.portlist:
            for port in self.ast.portlist.ports:
                if isinstance(port, vast.Ioport):
                    if port.first:
                        port_items.append(port.first)
                        port_names.add(port.first.name)
                elif isinstance(port, (vast.Input, vast.Output, vast.Inout)):
                    port_items.append(port)
                    port_names.add(port.name)
                elif isinstance(port, vast.Port):
                    port_names.add(port.name)

        # 对于 Port 节点（只有名字没有类型），在 Decl 中查找类型
        if port_names:
            for item in self.ast.items:
                if isinstance(item, vast.Decl):
                    for decl in item.list:
                        if isinstance(decl, (vast.Input, vast.Output, vast.Inout)):
                            if decl.name in port_names:
                                port_items.append(decl)

        # 去重（按名字）
        seen = set()
        unique_items = []
        for decl in port_items:
            if decl.name not in seen:
                seen.add(decl.name)
                unique_items.append(decl)

        for decl in unique_items:
            cls = "Input" if isinstance(decl, vast.Input) else "Output" if isinstance(decl, vast.Output) else "Input"
            width = self._get_width(decl)
            name = decl.name
            self.lines.append(f'{self._ind}self.{name} = {cls}({width}, "{name}")')

        if unique_items:
            self.lines.append("")

    def _get_width(self, node: Any) -> str:
        """从 Width 节点或信号节点推导位宽表达式。"""
        width_node = getattr(node, "width", None)
        if width_node is None:
            return "1"
        return self._emit_expr(width_node)

    # -----------------------------------------------------------------
    # Internal signals
    # -----------------------------------------------------------------
    def _emit_internal_signals(self):
        emitted = []
        for item in self.ast.items:
            if isinstance(item, vast.Decl):
                for decl in item.list:
                    if isinstance(decl, (vast.Wire, vast.Reg, vast.Integer)):
                        if decl.name in self._port_names:
                            continue
                        if decl.name in self._mem_names:
                            continue
                        if decl.name in self._arr_names:
                            continue
                        cls = "Wire" if isinstance(decl, vast.Wire) else "Reg"
                        width = self._get_width(decl)
                        dims = getattr(decl, "dimensions", None)
                        if dims is not None:
                            # 有维度：可能是 Array 或 Memory
                            if decl.name in self._mem_names:
                                depth = self._dim_depth(dims)
                                self.lines.append(f'{self._ind}self.{decl.name} = Memory({width}, {depth}, "{decl.name}")')
                            else:
                                depth = self._dim_depth(dims)
                                vtype = "Wire" if isinstance(decl, vast.Wire) else "Reg"
                                self.lines.append(f'{self._ind}self.{decl.name} = Array({width}, {depth}, "{decl.name}", vtype={vtype})')
                        else:
                            self.lines.append(f'{self._ind}self.{decl.name} = {cls}({width}, "{decl.name}")')
                        emitted.append(decl.name)

        if emitted:
            self.lines.append("")

    def _dim_depth(self, dims: vast.Dimensions) -> str:
        """从 Dimensions 推导深度。只处理一维。"""
        if hasattr(dims, "lengths") and dims.lengths:
            length = dims.lengths[0]
            if isinstance(length, vast.Length):
                hi = self._emit_expr(length.msb)
                lo = self._emit_expr(length.lsb)
                try:
                    hi_val = int(hi)
                    lo_val = int(lo)
                    return str(hi_val - lo_val + 1)
                except ValueError:
                    return f"({hi} - {lo} + 1)"
        return "1"

    # -----------------------------------------------------------------
    # Body
    # -----------------------------------------------------------------
    def _emit_body(self):
        for item in self.ast.items:
            self._emit_item(item)

    def _emit_item(self, item: Any):
        if isinstance(item, (vast.Decl, vast.Parameter, vast.Localparam, vast.Genvar)):
            # 声明已在前面处理
            pass
        elif isinstance(item, (vast.Input, vast.Output, vast.Inout)):
            pass  # 已在前面处理
        elif isinstance(item, vast.Assign):
            self._emit_assign(item)
        elif isinstance(item, vast.Always):
            self._emit_always(item)
        elif isinstance(item, vast.InstanceList):
            self._emit_instance_list(item)
        elif isinstance(item, vast.GenerateStatement):
            self._emit_generate(item)
        elif isinstance(item, vast.Block):
            for stmt in item.statements:
                self._emit_stmt(stmt)
        elif isinstance(item, vast.Pragma):
            pass  # 忽略 pragma
        else:
            # 未知节点，尝试作为语句处理
            self._emit_stmt(item)

    # -----------------------------------------------------------------
    # Assign
    # -----------------------------------------------------------------
    def _emit_assign(self, node: vast.Assign):
        lhs = self._emit_lvalue(node.left)
        rhs = self._emit_expr(node.right)
        if lhs.startswith("Cat("):
            # Verilog: assign {a, b, c} = d;  rtlgen 无直接对应
            self.lines.append(f"{self._ind}# TODO: unpack assignment: {lhs} = {rhs}")
            self.lines.append(f"{self._ind}# Consider using Split() or manual bit slicing")
        else:
            self.lines.append(f"{self._ind}{lhs} <<= {rhs}")

    # -----------------------------------------------------------------
    # Always blocks
    # -----------------------------------------------------------------
    def _emit_always(self, node: vast.Always):
        sens = node.sens_list
        clock, reset, reset_async, reset_active_low = self._analyze_sensitivity(sens)

        stmt = node.statement
        if clock is None and reset is None:
            # combinational
            self._emit_comb_block(stmt)
        else:
            self._emit_seq_block(stmt, clock, reset, reset_async, reset_active_low)

    def _analyze_sensitivity(self, sens_list: vast.SensList) -> Tuple[Optional[str], Optional[str], bool, bool]:
        """分析敏感列表，返回 (clock, reset, reset_async, reset_active_low)。"""
        clock = None
        reset = None
        reset_async = False
        reset_active_low = False

        if sens_list is None:
            return None, None, False, False

        for s in sens_list.list:
            if s.type == "all" or s.type == "*":
                return None, None, False, False
            elif s.type == "posedge":
                name = s.sig.name if isinstance(s.sig, vast.Identifier) else str(s.sig)
                if clock is None:
                    clock = name
                else:
                    reset = name
                    reset_async = True
            elif s.type == "negedge":
                name = s.sig.name if isinstance(s.sig, vast.Identifier) else str(s.sig)
                if clock is None:
                    clock = name
                else:
                    reset = name
                    reset_async = True
                    reset_active_low = True
            elif s.type == "level":
                name = s.sig.name if isinstance(s.sig, vast.Identifier) else str(s.sig)
                if reset is None:
                    reset = name
                    reset_async = True

        return clock, reset, reset_async, reset_active_low

    def _emit_comb_block(self, stmt: vast.Block):
        if self._inside_for:
            # 在 for 循环内部，直接输出语句，不生成装饰器
            for s in stmt.statements if hasattr(stmt, "statements") else [stmt]:
                self._emit_stmt(s)
            return
        self.lines.append("")
        self.lines.append(f"{self._ind}@self.comb")
        self.lines.append(f"{self._ind}def _comb_logic():")
        self.indent_level += 1
        self._inside_comb = True
        for s in stmt.statements if hasattr(stmt, "statements") else [stmt]:
            self._emit_stmt(s)
        self._inside_comb = False
        self.indent_level -= 1

    def _emit_seq_block(self, stmt: vast.Block, clock: Optional[str], reset: Optional[str],
                        reset_async: bool, reset_active_low: bool):
        if self._inside_for:
            # 在 for 循环内部，不生成 seq 装饰器（通常不会出现在 generate-for 中）
            for s in stmt.statements if hasattr(stmt, "statements") else [stmt]:
                self._emit_stmt(s)
            return
        self.lines.append("")
        clock_expr = f"self.{clock}" if clock else "None"
        reset_expr = f"self.{reset}" if reset else "None"
        args = [clock_expr, reset_expr]
        if reset_async:
            args.append("reset_async=True")
        if reset_active_low:
            args.append("reset_active_low=True")
        self.lines.append(f"{self._ind}@self.seq({', '.join(args)})")
        self.lines.append(f"{self._ind}def _seq_logic():")
        self.indent_level += 1
        self._inside_seq = True
        self._always_clock = clock
        self._always_reset = reset
        self._reset_async = reset_async
        self._reset_active_low = reset_active_low
        for s in stmt.statements if hasattr(stmt, "statements") else [stmt]:
            self._emit_stmt(s)
        self._reset_async = False
        self._reset_active_low = False
        self._always_reset = None
        self._always_clock = None
        self._inside_seq = False
        self.indent_level -= 1

    # -----------------------------------------------------------------
    # Statements
    # -----------------------------------------------------------------
    def _emit_stmt(self, stmt: Any):
        if stmt is None:
            return
        if isinstance(stmt, vast.BlockingSubstitution):
            lhs = self._emit_lvalue(stmt.left)
            rhs = self._emit_expr(stmt.right)
            op = "<<="
            self.lines.append(f"{self._ind}{lhs} {op} {rhs}")
        elif isinstance(stmt, vast.NonblockingSubstitution):
            lhs = self._emit_lvalue(stmt.left)
            rhs = self._emit_expr(stmt.right)
            op = "<<="
            self.lines.append(f"{self._ind}{lhs} {op} {rhs}")
        elif isinstance(stmt, vast.IfStatement):
            self._emit_if(stmt)
        elif isinstance(stmt, vast.CaseStatement):
            self._emit_case(stmt)
        elif isinstance(stmt, vast.ForStatement):
            self._emit_for(stmt)
        elif isinstance(stmt, vast.Block):
            for s in stmt.statements:
                self._emit_stmt(s)
        elif isinstance(stmt, vast.Assign):
            self._emit_assign(stmt)
        elif isinstance(stmt, vast.Always):
            self._emit_always(stmt)
        elif isinstance(stmt, (vast.Decl,)):
            pass
        else:
            # 未知语句，尝试表达式化
            expr = self._emit_expr(stmt)
            if expr:
                self.lines.append(f"{self._ind}# unhandled statement: {expr}")

    def _emit_if(self, node: vast.IfStatement):
        cond = self._emit_expr(node.cond)
        self.lines.append(f"{self._ind}with If({cond}):")
        self.indent_level += 1
        for s in node.true_statement.statements if hasattr(node.true_statement, "statements") else [node.true_statement]:
            self._emit_stmt(s)
        self.indent_level -= 1

        false_stmt = node.false_statement
        if false_stmt is None:
            return

        self._emit_else_chain(false_stmt)

    def _emit_else_chain(self, false_stmt: Any):
        """递归处理 else / else-if 链，确保缩进正确。"""
        self.lines.append(f"{self._ind}with Else():")
        self.indent_level += 1

        if isinstance(false_stmt, vast.IfStatement):
            cond = self._emit_expr(false_stmt.cond)
            self.lines.append(f"{self._ind}with If({cond}):")
            self.indent_level += 1
            for s in false_stmt.true_statement.statements if hasattr(false_stmt.true_statement, "statements") else [false_stmt.true_statement]:
                self._emit_stmt(s)
            self.indent_level -= 1

            if false_stmt.false_statement is not None:
                self._emit_else_chain(false_stmt.false_statement)
        else:
            for s in false_stmt.statements if hasattr(false_stmt, "statements") else [false_stmt]:
                self._emit_stmt(s)

        self.indent_level -= 1

    def _emit_case(self, node: vast.CaseStatement):
        expr = self._emit_expr(node.comp)
        self.lines.append(f"{self._ind}with Switch({expr}) as sw:")
        self.indent_level += 1
        for case in node.caselist:
            if case.cond is None:
                # default
                self.lines.append(f"{self._ind}with sw.default():")
                self.indent_level += 1
                for s in case.statement.statements if hasattr(case.statement, "statements") else [case.statement]:
                    self._emit_stmt(s)
                self.indent_level -= 1
            else:
                cond = case.cond
                if isinstance(cond, (list, tuple)):
                    # 多个 case 条件，如 case 0, 1: ...
                    # rtlgen Switch 只支持单个值，取第一个并注释
                    first_cond = cond[0] if cond else None
                    cond_str = self._emit_expr(first_cond) if first_cond else "0"
                    if len(cond) > 1:
                        others = ", ".join(self._emit_expr(c) for c in cond[1:])
                        self.lines.append(f"{self._ind}# Note: merged case values: {others}")
                else:
                    cond_str = self._emit_expr(cond)
                self.lines.append(f"{self._ind}with sw.case({cond_str}):")
                self.indent_level += 1
                for s in case.statement.statements if hasattr(case.statement, "statements") else [case.statement]:
                    self._emit_stmt(s)
                self.indent_level -= 1
        self.indent_level -= 1

    def _emit_for(self, node: vast.ForStatement):
        """将 for 循环转换为 ForGen（generate-for）或普通 Python for。"""
        init = node.pre
        cond = node.cond
        update = node.post
        body = node.statement

        # 尝试识别 generate-for 模式
        var_name = None
        start = None
        end = None

        if isinstance(init, vast.BlockingSubstitution):
            init_var = init.left
            if isinstance(init_var, vast.Lvalue):
                init_var = init_var.var
            if isinstance(init_var, vast.Identifier):
                var_name = init_var.name
                start = self._emit_expr(init.right)

        if isinstance(cond, vast.LessThan):
            cond_left = cond.left
            if isinstance(cond_left, vast.Lvalue):
                cond_left = cond_left.var
            if isinstance(cond_left, vast.Identifier) and cond_left.name == var_name:
                end = self._emit_expr(cond.right)

        old_inside_for = self._inside_for
        old_local_vars = set(self._local_vars)
        if var_name:
            self._local_vars.add(var_name)

        if var_name and start is not None and end is not None:
            try:
                s = int(start)
                e = int(end)
                self.lines.append(f'{self._ind}with ForGen("{var_name}", {s}, {e}) as {var_name}:')
                self.indent_level += 1
                for stmt in body.statements if hasattr(body, "statements") else [body]:
                    self._emit_stmt(stmt)
                self.indent_level -= 1
                self._local_vars = old_local_vars
                return
            except ValueError:
                pass

        # 回退：普通 for 循环（参数化 end，不可综合但保留语义）
        self.lines.append(f"{self._ind}# for-loop (non-generate) - parameter-driven")
        self.lines.append(f"{self._ind}for {var_name} in range({start}, {end}):")
        self.indent_level += 1
        self._inside_for = True
        for stmt in body.statements if hasattr(body, "statements") else [body]:
            self._emit_stmt(stmt)
        self._inside_for = old_inside_for
        self.indent_level -= 1
        self._local_vars = old_local_vars

    # -----------------------------------------------------------------
    # Generate blocks
    # -----------------------------------------------------------------
    def _emit_generate(self, node: vast.GenerateStatement):
        for item in node.items:
            if isinstance(item, vast.ForStatement):
                self._emit_for(item)
            elif isinstance(item, vast.IfStatement):
                cond = self._emit_expr(item.cond)
                self.lines.append(f"{self._ind}with GenIf({cond}):")
                self.indent_level += 1
                for s in item.true_statement.statements if hasattr(item.true_statement, "statements") else [item.true_statement]:
                    self._emit_stmt(s)
                self.indent_level -= 1
                if item.false_statement:
                    self.lines.append(f"{self._ind}with GenElse():")
                    self.indent_level += 1
                    for s in item.false_statement.statements if hasattr(item.false_statement, "statements") else [item.false_statement]:
                        self._emit_stmt(s)
                    self.indent_level -= 1
            elif isinstance(item, vast.Block):
                for s in item.statements:
                    self._emit_stmt(s)
            else:
                self._emit_item(item)

    # -----------------------------------------------------------------
    # Instance
    # -----------------------------------------------------------------
    def _emit_instance_list(self, node: vast.InstanceList):
        for inst in node.instances:
            self._emit_instance(inst)

    def _emit_instance(self, node: vast.Instance):
        mod_name = node.module
        inst_name = node.name

        # 参数映射
        params = {}
        for param in node.parameterlist:
            if isinstance(param, vast.ParamArg):
                params[param.paramname] = self._emit_expr(param.argname)

        # 端口映射
        port_map = {}
        for port in node.portlist:
            if isinstance(port, vast.PortArg):
                port_map[port.portname] = self._emit_expr(port.argname)

        self.lines.append("")
        if params:
            self.lines.append(f"{self._ind}{inst_name} = {mod_name}({', '.join(f'{k}={v}' for k, v in params.items())})")
        else:
            self.lines.append(f"{self._ind}{inst_name} = {mod_name}()")

        port_map_lines = [f'"{k}": {v}' for k, v in port_map.items()]
        self.lines.append(f"{self._ind}self.instantiate(")
        self.lines.append(f"{self._ind}    {inst_name},")
        self.lines.append(f'    {self._ind}"{inst_name}",')
        if params:
            self.lines.append(f"{self._ind}    params={{{', '.join(f'{k!r}: {v}' for k, v in params.items())}}},")
        self.lines.append(f"{self._ind}    port_map={{")
        for line in port_map_lines:
            self.lines.append(f"{self._ind}        {line},")
        self.lines.append(f"{self._ind}    }},")
        self.lines.append(f"{self._ind})")

    # -----------------------------------------------------------------
    # Expressions
    # -----------------------------------------------------------------
    def _emit_lvalue(self, node: Any) -> str:
        """生成赋值左值的 Python 表达式。"""
        if isinstance(node, vast.Identifier):
            return f"self.{node.name}"
        elif isinstance(node, vast.Partselect):
            var = self._emit_expr(node.var)
            hi = self._emit_expr(node.msb)
            lo = self._emit_expr(node.lsb)
            return f"{var}[{hi}:{lo}]"
        elif isinstance(node, vast.Pointer):
            var = self._emit_expr(node.var)
            ptr = self._emit_expr(node.ptr)
            return f"{var}[{ptr}]"
        else:
            return self._emit_expr(node)

    def _emit_expr(self, node: Any) -> str:
        if node is None:
            return "None"
        if isinstance(node, vast.Identifier):
            name = node.name
            if name in self._local_vars:
                return name
            if name in self._param_names or name in self._localparam_names:
                return f"self.{name}"
            return f"self.{name}"
        if isinstance(node, vast.IntConst):
            return self._emit_intconst(node.value)
        if isinstance(node, vast.FloatConst):
            return str(node.value)
        if isinstance(node, vast.StringConst):
            return repr(node.value)
        if isinstance(node, vast.Constant):
            return str(node.value)
        if isinstance(node, vast.Partselect):
            var = self._emit_expr(node.var)
            hi = self._emit_expr(node.msb)
            lo = self._emit_expr(node.lsb)
            return f"{var}[{hi}:{lo}]"
        if isinstance(node, vast.Pointer):
            var = self._emit_expr(node.var)
            ptr = self._emit_expr(node.ptr)
            return f"{var}[{ptr}]"
        if isinstance(node, vast.Concat):
            parts = ", ".join(self._emit_expr(c) for c in node.list)
            return f"Cat({parts})"
        if isinstance(node, vast.Repeat):
            value = self._emit_expr(node.value)
            times = self._emit_expr(node.times)
            return f"Rep({value}, {times})"
        if isinstance(node, vast.UnaryOperator):
            op = self._UNARYOP_MAP.get(node.__class__.__name__, "?")
            operand = self._emit_expr(node.right)
            if op == "not ":
                return f"(not {operand})"
            return f"({op}{operand})"
        if isinstance(node, vast.Cond):
            # Cond 是 Operator 的子类，必须先检查
            cond = self._emit_expr(node.cond)
            true_val = self._emit_expr(node.true_value)
            false_val = self._emit_expr(node.false_value)
            return f"Mux({cond}, {true_val}, {false_val})"
        if isinstance(node, vast.Operator):
            op = self._BINOP_MAP.get(node.__class__.__name__, "?")
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} {op} {right})"
        if isinstance(node, vast.Minus):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} - {right})"
        if isinstance(node, vast.Plus):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} + {right})"
        if isinstance(node, vast.Times):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} * {right})"
        if isinstance(node, vast.Divide):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} // {right})"
        if isinstance(node, vast.Mod):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} % {right})"
        if isinstance(node, vast.Power):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} ** {right})"
        if isinstance(node, vast.Sll):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} << {right})"
        if isinstance(node, vast.Srl):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} >> {right})"
        if isinstance(node, vast.Sra):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} >>> {right})"
        if isinstance(node, vast.Land):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} & {right})"
        if isinstance(node, vast.Lor):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} | {right})"
        if isinstance(node, vast.Eq):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} == {right})"
        if isinstance(node, vast.NotEq):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} != {right})"
        if isinstance(node, vast.LessThan):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} < {right})"
        if isinstance(node, vast.GreaterThan):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} > {right})"
        if isinstance(node, vast.LessEq):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} <= {right})"
        if isinstance(node, vast.GreaterEq):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} >= {right})"
        if isinstance(node, vast.And):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} & {right})"
        if isinstance(node, vast.Or):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} | {right})"
        if isinstance(node, vast.Xor):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} ^ {right})"
        if isinstance(node, vast.Xnor):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return f"({left} ^~ {right})"
        if isinstance(node, vast.Ulnot):
            operand = self._emit_expr(node.right)
            return f"(~{operand})"
        if isinstance(node, vast.Unot):
            operand = self._emit_expr(node.right)
            return f"(not {operand})"
        if isinstance(node, vast.Uplus):
            operand = self._emit_expr(node.right)
            return f"(+{operand})"
        if isinstance(node, vast.Uminus):
            operand = self._emit_expr(node.right)
            return f"(-{operand})"
        if isinstance(node, vast.Uand):
            operand = self._emit_expr(node.right)
            return f"(&{operand})"
        if isinstance(node, vast.Uor):
            operand = self._emit_expr(node.right)
            return f"(|{operand})"
        if isinstance(node, vast.Uxor):
            operand = self._emit_expr(node.right)
            return f"(^{operand})"
        if isinstance(node, vast.Width):
            msb = self._emit_expr(node.msb)
            lsb = self._emit_expr(node.lsb)
            try:
                m = int(msb)
                l = int(lsb)
                return str(m - l + 1)
            except ValueError:
                return f"({msb} - {lsb} + 1)"
        if isinstance(node, vast.Lvalue):
            return self._emit_lvalue(node.var)
        if isinstance(node, vast.Rvalue):
            return self._emit_expr(node.var)
        if isinstance(node, vast.SensList):
            return ", ".join(self._emit_expr(s) for s in node.list)
        if isinstance(node, vast.Sens):
            if node.type == "all":
                return "*"
            sig = self._emit_expr(node.sig)
            return f"{node.type} {sig}"
        if isinstance(node, vast.ParamArg):
            return self._emit_expr(node.argname)
        if isinstance(node, vast.PortArg):
            return self._emit_expr(node.argname)
        if isinstance(node, vast.Length):
            msb = self._emit_expr(node.msb)
            lsb = self._emit_expr(node.lsb)
            return f"({msb}:{lsb})"
        if isinstance(node, vast.Dimensions):
            return ", ".join(self._emit_expr(d) for d in node.dimensions)
        if isinstance(node, vast.Genvar):
            return node.name
        if isinstance(node, (vast.Parameter, vast.Localparam)):
            return f"self.{node.name}"
        if isinstance(node, vast.Block):
            return "# block"
        if isinstance(node, vast.Function):
            return f"# function {node.name}"
        if isinstance(node, vast.Task):
            return f"# task {node.name}"

        # 回退
        cls_name = node.__class__.__name__
        return f"# <{cls_name}>"

    def _emit_intconst(self, value: str) -> str:
        """将 Verilog 整数常量转换为 Python 整数。"""
        value = value.strip().replace("_", "")
        # 处理 'd/'h/'b/'o 格式
        m = re.match(r"(\d+)?'([sS]?)([dDbBhHoO])([0-9a-fA-F_xzXZ]+)", value)
        if m:
            width_str, signed, base, digits = m.groups()
            base_map = {"d": 10, "D": 10, "h": 16, "H": 16, "b": 2, "B": 2, "o": 8, "O": 8}
            b = base_map.get(base, 10)
            # 去除 x/z（不可综合的部分）
            digits = digits.replace("x", "0").replace("X", "0").replace("z", "0").replace("Z", "0")
            try:
                val = int(digits, b)
                return str(val)
            except ValueError:
                return value
        # 处理无尺寸常量如 '0, '1, 'b0, 'b1, 'x
        m2 = re.match(r"'(0|1|x|X|z|Z)$", value)
        if m2:
            v = m2.group(1).lower()
            return "0" if v in ("x", "z") else v
        # 处理 'b0, 'b1 等（无尺寸）
        m3 = re.match(r"'([bB])([01_xzXZ]+)$", value)
        if m3:
            digits = m3.group(2).replace("x", "0").replace("X", "0").replace("z", "0").replace("Z", "0")
            try:
                return str(int(digits, 2))
            except ValueError:
                return value
        try:
            return str(int(value))
        except ValueError:
            return value

    def _emit_class_footer(self):
        pass
