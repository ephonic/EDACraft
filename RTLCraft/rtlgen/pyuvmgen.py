"""
rtlgen.pyuvmgen — Python UVM -> SystemVerilog/UVM 代码生成器

遍历 rtlgen.pyuvm 构建的 Python 对象树，转译为原生 SV/UVM。
"""
from __future__ import annotations

import ast
import inspect
import re
import sys
import textwrap
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from rtlgen.core import Input, Module, Output
from rtlgen.pyuvm import (
    UVMAgent,
    UVMAnalysisImp,
    UVMAnalysisPort,
    UVMComponent,
    UVMDriver,
    UVMEnv,
    UVMField,
    UVMMonitor,
    UVMReg,
    UVMRegBlock,
    UVMRegField,
    UVMRegPredictor,
    UVMScoreboard,
    UVMSequence,
    UVMSequenceItem,
    UVMSequencer,
    UVMTest,
    UVMVirtualSequence,
)


class UVMEmitter:
    """基于 pyuvm Python 树的 UVM 代码发射器。"""

    def __init__(self, indent: str = "    "):
        self.indent = indent

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def emit(self, test: UVMTest, pkg_name: str = "test_pkg") -> Dict[str, str]:
        """为指定的 UVMTest 生成全套 SV/UVM 文件。"""
        files: Dict[str, str] = {}

        # 收集 test 树中涉及的所有类
        all_classes = self._collect_classes(test)

        # 扫描所有 vif.cb 额外信号（非 DUT 端口但在 Python 代码中被引用）
        vif_extra = self._collect_vif_extra_signals(all_classes["components"])

        # interface & tb_top（如果 test 关联了 dut）
        dut = getattr(test, "dut", None)
        if_name = None
        clk = None
        if isinstance(dut, Module):
            if_name = f"{dut.name}_if"
            clk = self._find_clock(dut)
            files[f"{if_name}.sv"] = self._emit_interface(dut, if_name, clk, vif_extra)
            files["tb_top.sv"] = self._emit_tb_top(dut, test.name, if_name, clk)

        files[f"{pkg_name}.sv"] = self._emit_pkg(pkg_name, all_classes)

        # 生成 transaction
        for txn_cls in all_classes["transactions"]:
            files[f"{txn_cls.__name__}.sv"] = self._emit_transaction(txn_cls, pkg_name)

        # 生成 component（按类去重）
        generated: Set[Type[UVMComponent]] = set()
        for comp_cls in all_classes["components"]:
            if comp_cls in generated:
                continue
            generated.add(comp_cls)
            files[f"{self._to_snake(comp_cls.__name__)}.sv"] = self._emit_component_class(
                comp_cls, pkg_name, if_name
            )

        return files

    # -----------------------------------------------------------------
    # Collectors
    # -----------------------------------------------------------------
    def _collect_classes(self, root: UVMComponent) -> Dict[str, List[Type[Any]]]:
        transactions: Set[Type[UVMSequenceItem]] = set()
        components: Set[Type[UVMComponent]] = set()
        visited: Set[Type[Any]] = set()

        def add(cls: Type[Any]):
            if cls in visited:
                return
            visited.add(cls)
            if issubclass(cls, UVMRegField):
                return
            if issubclass(cls, UVMSequenceItem):
                if cls is not UVMSequenceItem:
                    transactions.add(cls)
            elif issubclass(cls, UVMComponent):
                if cls not in (UVMComponent, UVMAgent, UVMEnv, UVMTest, UVMMonitor, UVMDriver, UVMSequencer, UVMScoreboard, UVMSequence, UVMVirtualSequence, UVMRegBlock, UVMRegPredictor):
                    components.add(cls)

        # BFS 从 test 类开始扫描方法体 AST 中引用的所有 UVM 类
        queue = [root.__class__]

        while queue:
            cls = queue.pop(0)
            add(cls)
            for attr_name, attr_val in cls.__dict__.items():
                if not callable(attr_val):
                    continue
                try:
                    src = inspect.getsource(attr_val)
                except (TypeError, OSError):
                    continue
                tree = ast.parse(textwrap.dedent(src))
                for node in ast.walk(tree):
                    # Name 引用
                    if isinstance(node, ast.Name):
                        ref = getattr(attr_val, "__globals__", {}).get(node.id)
                        if isinstance(ref, type) and issubclass(ref, (UVMComponent, UVMSequenceItem)) and ref not in visited and ref not in queue:
                            queue.append(ref)
                    # create(Cls, ...) 中的 Cls
                    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "create":
                        if node.args and isinstance(node.args[0], ast.Name):
                            ref = getattr(attr_val, "__globals__", {}).get(node.args[0].id)
                            if isinstance(ref, type) and issubclass(ref, (UVMComponent, UVMSequenceItem)) and ref not in visited and ref not in queue:
                                queue.append(ref)
                    # 函数参数中的类引用（如 txn_type=CounterTxn）
                    elif isinstance(node, ast.Call):
                        for arg in node.args:
                            if isinstance(arg, ast.Name):
                                ref = getattr(attr_val, "__globals__", {}).get(arg.id)
                                if isinstance(ref, type) and issubclass(ref, (UVMComponent, UVMSequenceItem)) and ref not in visited and ref not in queue:
                                    queue.append(ref)
                        for kw in node.keywords:
                            if isinstance(kw.value, ast.Name):
                                ref = getattr(attr_val, "__globals__", {}).get(kw.value.id)
                                if isinstance(ref, type) and issubclass(ref, (UVMComponent, UVMSequenceItem)) and ref not in visited and ref not in queue:
                                    queue.append(ref)

        # 同时扫描实例树中 driver 的 txn_type
        for comp in self._walk_tree(root):
            if isinstance(comp, UVMDriver) and comp.txn_type is not None:
                add(comp.txn_type)

        return {
            "transactions": sorted(transactions, key=lambda c: c.__name__),
            "components": sorted(components, key=lambda c: c.__name__),
        }

    def _walk_tree(self, root: UVMComponent) -> List[UVMComponent]:
        result = [root]
        for child in root.children:
            result.extend(self._walk_tree(child))
        return result

    def _collect_vif_extra_signals(self, component_classes: List[Type[UVMComponent]]) -> Set[str]:
        """Scan all component methods for self.vif.cb.xxx references."""
        extras: Set[str] = set()
        for cls in component_classes:
            for attr_name, attr_val in cls.__dict__.items():
                if not callable(attr_val):
                    continue
                try:
                    src = inspect.getsource(attr_val)
                except (TypeError, OSError):
                    continue
                tree = ast.parse(textwrap.dedent(src))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute):
                        base = self._expr_to_sv(node.value)
                        if base == "vif.cb":
                            extras.add(node.attr)
        return extras

    # -----------------------------------------------------------------
    # Transaction emission
    # -----------------------------------------------------------------
    @staticmethod
    def _file_header(filename: str, module_name: str = "") -> str:
        return f"""// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : {filename}
// Module Name : {module_name or filename.replace('.sv', '')}
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

"""

    def _emit_transaction(self, cls: Type[UVMSequenceItem], pkg_name: str) -> str:
        name = cls.__name__
        fname = f"{name}.sv"
        raw_fields = getattr(cls, "_fields", [])
        fields: List[UVMField] = []
        for f in raw_fields:
            if isinstance(f, tuple):
                fields.append(UVMField(f[0], f[1] if len(f) > 1 else 1, f[2] if len(f) > 2 else "UVM_ALL_ON"))
            else:
                fields.append(f)
        field_decls = []
        field_macros = []
        for f in fields:
            sv_w = f"[{f.width - 1}:0] " if f.width > 1 else ""
            field_decls.append(f"    rand logic {sv_w}{f.name};")
            field_macros.append(f'        `uvm_field_int({f.name}, {f.access})')
        decl_str = "\n".join(field_decls)
        macro_str = "\n".join(field_macros)
        header = self._file_header(fname, name)
        return f"""{header}`ifndef {name.upper()}_SV
`define {name.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {name} extends uvm_sequence_item;
    `uvm_object_utils_begin({name})
{macro_str}
    `uvm_object_utils_end

{decl_str}

    function new(string name = "{name}");
        super.new(name);
    endfunction

endclass : {name}

`endif // {name.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Component class emission
    # -----------------------------------------------------------------
    def _emit_component_class(self, cls: Type[UVMComponent], pkg_name: str, if_name: Optional[str] = None) -> str:
        name = cls.__name__
        fname = f"{self._to_snake(name)}.sv"

        # RAL 占位类生成（简化实现，确保 SV 编译通过）
        if issubclass(cls, (UVMRegBlock, UVMRegPredictor)) and cls not in (UVMRegBlock, UVMRegPredictor):
            header = self._file_header(fname, name)
            return f"""{header}`ifndef {name.upper()}_SV
`define {name.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {name} extends uvm_component;
    `uvm_component_utils({name})

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

endclass : {name}

`endif // {name.upper()}_SV
"""

        base = self._uvm_base_name(cls)
        member_decls = self._component_member_decls(cls, if_name)
        utils_macro = f"    `uvm_component_utils({name})" if base != "uvm_sequence" else f"    `uvm_object_utils({name})"

        init_body = self._translate_method(cls, "__init__", skip_base=True)
        build_body = self._translate_method(cls, "build_phase")
        connect_body = self._translate_method(cls, "connect_phase")
        end_of_elab_body = self._translate_method(cls, "end_of_elaboration_phase")
        run_body = self._translate_method(cls, "run_phase")
        body_task = self._translate_method(cls, "body")
        pre_body = self._translate_method(cls, "pre_body")
        post_body = self._translate_method(cls, "post_body")
        write_body = self._translate_method(cls, "write")
        report_body = self._translate_method(cls, "report_phase")

        sections: List[str] = []
        if member_decls:
            sections.append(member_decls)
        if init_body:
            new_base = "uvm_component" if base != "uvm_sequence" else "uvm_sequence"
            new_args = "string name, uvm_component parent" if base != "uvm_sequence" else 'string name = ""'
            sections.append(f"    function new({new_args});\n{init_body}\n    endfunction")
        if build_body or (if_name and issubclass(cls, (UVMDriver, UVMMonitor)) and self._class_uses_vif(cls)):
            build_lines = ["        super.build_phase(phase);"]
            if build_body:
                build_lines.append(build_body)
            if if_name and issubclass(cls, (UVMDriver, UVMMonitor)) and self._class_uses_vif(cls):
                build_lines.append(f'        if (!uvm_config_db#(virtual {if_name})::get(this, "", "vif", vif))')
                build_lines.append('            `uvm_fatal("NOVIF", "Virtual interface not found")')
            sections.append(f"    virtual function void build_phase(uvm_phase phase);\n" + "\n".join(build_lines) + "\n    endfunction")
        if connect_body:
            sections.append(f"    virtual function void connect_phase(uvm_phase phase);\n        super.connect_phase(phase);\n{connect_body}\n    endfunction")
        if end_of_elab_body:
            sections.append(f"    virtual function void end_of_elaboration_phase(uvm_phase phase);\n{end_of_elab_body}\n    endfunction")
        if run_body:
            sections.append(f"    virtual task run_phase(uvm_phase phase);\n{run_body}\n    endtask")
        if pre_body:
            sections.append(f"    virtual task pre_body();\n{pre_body}\n    endtask")
        if body_task:
            sections.append(f"    virtual task body();\n{body_task}\n    endtask")
        if post_body:
            sections.append(f"    virtual task post_body();\n{post_body}\n    endtask")
        if write_body:
            txn_type = self._resolve_txn_type(cls) or "uvm_sequence_item"
            sections.append(f"    virtual function void write({txn_type} txn);\n{write_body}\n    endfunction")
        if report_body:
            sections.append(f"    virtual function void report_phase(uvm_phase phase);\n{report_body}\n    endfunction")

        sections.extend(self._extra_method_sections(cls))
        dpi_imports = self._collect_dpi_imports(cls)
        sections_str = "\n\n".join(sections)
        header = self._file_header(fname, name)
        dpi_str = "\n".join(dpi_imports)
        if dpi_str:
            dpi_str = dpi_str + "\n"
        return f"""{header}`ifndef {name.upper()}_SV
`define {name.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"
{dpi_str}
class {name} extends {base};
{utils_macro}

{sections_str}

endclass : {name}

`endif // {name.upper()}_SV
"""

    def _collect_dpi_imports(self, cls: Type[UVMComponent]) -> List[str]:
        imports: List[str] = []
        seen = set()
        for method_name in dir(cls):
            if method_name.startswith("__") or not callable(getattr(cls, method_name, None)):
                continue
            method = getattr(cls, method_name)
            try:
                src = inspect.getsource(method)
            except (TypeError, OSError):
                continue
            src = textwrap.dedent(src)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    ref = getattr(method, "__globals__", {}).get(func_name)
                    if callable(ref):
                        c_decl = getattr(ref, "_sv_dpi", None)
                        if c_decl and c_decl not in seen:
                            seen.add(c_decl)
                            imports.append(c_decl)
        return imports

    def _extra_method_sections(self, cls: Type[UVMComponent]) -> List[str]:
        sections: List[str] = []
        txn_type = self._resolve_txn_type(cls) or "uvm_sequence_item"
        known_methods = {
            "__init__", "build_phase", "connect_phase", "end_of_elaboration_phase",
            "run_phase", "body", "pre_body", "post_body", "write", "report_phase"
        }
        for method_name, method in cls.__dict__.items():
            if method_name in known_methods or method_name.startswith("_") or not callable(method):
                continue
            if isinstance(method, (staticmethod, classmethod)):
                continue
            sv_body = self._translate_method(cls, method_name)
            if not sv_body:
                continue
            try:
                src = inspect.getsource(method)
                src = textwrap.dedent(src)
                tree = ast.parse(src)
                func_def = tree.body[0]
                assert isinstance(func_def, (ast.FunctionDef, ast.AsyncFunctionDef))
            except Exception:
                continue
            arg_types: Dict[str, str] = {}
            for arg in func_def.args.args:
                arg_name = arg.arg
                if arg_name == "self":
                    continue
                uses_attr = False
                for node in ast.walk(func_def):
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == arg_name:
                        uses_attr = True
                        break
                arg_types[arg_name] = txn_type if uses_attr else "int"
            args_str = ", ".join(f"{arg_types.get(a.arg, 'int')} {a.arg}" for a in func_def.args.args if a.arg != "self")
            if isinstance(func_def, ast.AsyncFunctionDef):
                sections.append(f"    virtual task {method_name}({args_str});\n{sv_body}\n    endtask")
            else:
                sections.append(f"    virtual function void {method_name}({args_str});\n{sv_body}\n    endfunction")
        return sections

    def _class_uses_vif(self, cls: Type[UVMComponent]) -> bool:
        for method_name in ("__init__", "build_phase", "connect_phase", "run_phase", "body"):
            if not hasattr(cls, method_name):
                continue
            method = getattr(cls, method_name)
            try:
                src = inspect.getsource(method)
            except (TypeError, OSError):
                continue
            tree = ast.parse(textwrap.dedent(src))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    base = self._expr_to_sv(node.value)
                    if base in ("vif.cb", "self.vif", "vif"):
                        return True
        return False

    def _uvm_base_name(self, cls: Type[UVMComponent]) -> str:
        txn = self._resolve_txn_type(cls) or getattr(cls, "_txn_type_name", "uvm_sequence_item")
        if issubclass(cls, UVMTest):
            return "uvm_test"
        if issubclass(cls, UVMEnv):
            return "uvm_env"
        if issubclass(cls, UVMAgent):
            return "uvm_agent"
        if issubclass(cls, UVMScoreboard):
            return "uvm_scoreboard"
        if issubclass(cls, UVMMonitor):
            return "uvm_monitor"
        if issubclass(cls, UVMDriver):
            return f"uvm_driver #({txn})"
        if issubclass(cls, UVMSequencer):
            return f"uvm_sequencer #({txn})"
        if issubclass(cls, UVMVirtualSequence):
            return f"uvm_sequence #({txn})"
        if issubclass(cls, UVMSequence):
            return f"uvm_sequence #({txn})"
        if issubclass(cls, (UVMRegBlock, UVMRegPredictor)):
            return "uvm_component"
        return "uvm_component"

    def _resolve_txn_type(self, cls: Type[Any]) -> Optional[str]:
        """尝试从 __init__ 或 body()/run_phase() 源码中解析 txn_type 参数对应的类名。"""
        # 1. 尝试从 __init__ 解析
        try:
            src = inspect.getsource(cls.__init__)
        except (TypeError, OSError):
            src = None
        if src:
            tree = ast.parse(textwrap.dedent(src))
            func_def = tree.body[0]
            assert isinstance(func_def, (ast.FunctionDef, ast.AsyncFunctionDef))
            for node in ast.walk(func_def):
                if isinstance(node, ast.Call):
                    func = node.func
                    is_super_init = False
                    if isinstance(func, ast.Attribute) and func.attr == "__init__":
                        if isinstance(func.value, ast.Call) and isinstance(func.value.func, ast.Name) and func.value.func.id == "super":
                            is_super_init = True
                    if is_super_init:
                        for kw in node.keywords:
                            if kw.arg == "txn_type" and isinstance(kw.value, ast.Name):
                                ref = getattr(cls.__init__, "__globals__", {}).get(kw.value.id)
                                if isinstance(ref, type) and issubclass(ref, UVMSequenceItem):
                                    return ref.__name__
                        if len(node.args) >= 3:
                            arg = node.args[2]
                            if isinstance(arg, ast.Name):
                                ref = getattr(cls.__init__, "__globals__", {}).get(arg.id)
                                if isinstance(ref, type) and issubclass(ref, UVMSequenceItem):
                                    return ref.__name__
        # 2. 对于 sequence，尝试从 body() 中找 create(SomeClass, ...)
        if issubclass(cls, UVMSequence):
            txn = self._resolve_txn_type_from_method(cls, "body")
            if txn:
                return txn
        # 3. 对于 driver/monitor/scoreboard，尝试从 run_phase()/write() 中找 create(SomeClass, ...)
        for method_name in ("run_phase", "write"):
            txn = self._resolve_txn_type_from_method(cls, method_name)
            if txn:
                return txn
        # 4. fallback: 如果类所在模块中只有一个 UVMSequenceItem 子类，则使用它
        mod = sys.modules.get(cls.__module__)
        if mod:
            candidates = [
                obj for obj in mod.__dict__.values()
                if isinstance(obj, type)
                and issubclass(obj, UVMSequenceItem)
                and obj is not UVMSequenceItem
            ]
            if len(candidates) == 1:
                return candidates[0].__name__
        return None

    def _resolve_txn_type_from_method(self, cls: Type[Any], method_name: str) -> Optional[str]:
        if not hasattr(cls, method_name):
            return None
        method = getattr(cls, method_name)
        try:
            src = inspect.getsource(method)
        except (TypeError, OSError):
            return None
        tree = ast.parse(textwrap.dedent(src))
        func_def = tree.body[0]
        assert isinstance(func_def, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "create":
                if node.args and isinstance(node.args[0], ast.Name):
                    ref = getattr(method, "__globals__", {}).get(node.args[0].id)
                    if isinstance(ref, type) and issubclass(ref, UVMSequenceItem):
                        return ref.__name__
        return None

    def _component_member_decls(self, cls: Type[UVMComponent], if_name: Optional[str] = None) -> str:
        lines: List[str] = []
        seen = set()
        txn_type = self._resolve_txn_type(cls) or "uvm_sequence_item"
        uses_vif = False

        def _infer_sv_type(value_node: ast.AST) -> Optional[str]:
            if isinstance(value_node, ast.Constant):
                if isinstance(value_node.value, bool):
                    return "bit"
                if isinstance(value_node.value, int):
                    return "int"
                if isinstance(value_node.value, str):
                    return "string"
                return None
            if isinstance(value_node, ast.List):
                return None  # 复杂类型暂不推断
            if isinstance(value_node, ast.Call):
                func = value_node.func
                cls_name = None
                if isinstance(func, ast.Name):
                    cls_name = func.id
                elif isinstance(func, ast.Attribute):
                    cls_name = func.attr
                if cls_name:
                    if cls_name == "Coverage":
                        return "Coverage"
                    if cls_name == "UVMSequencer":
                        return f"uvm_sequencer #({txn_type})"
                    if cls_name == "UVMAnalysisFIFO":
                        return f"uvm_tlm_analysis_fifo #({txn_type})"
                    if cls_name == "UVMBlockingGetPort":
                        return f"uvm_blocking_get_port #({txn_type})"
                    if cls_name == "UVMAnalysisPort":
                        return f"uvm_analysis_port #({txn_type})"
                    if cls_name == "UVMAnalysisImp":
                        return f"uvm_analysis_imp #({txn_type}, {cls.__name__})"
                    if cls_name in ("UVMDriver", "UVMMonitor", "UVMAgent", "UVMEnv", "UVMScoreboard", "UVMSequence", "UVMSequencer"):
                        return cls_name
                    return cls_name
            return None

        def _process_attr(attr: str, value_node: ast.AST):
            nonlocal seen
            if attr in seen or attr.startswith("_") or attr in ("seq_item_port",):
                return
            seen.add(attr)
            if attr == "exp":
                lines.append(f"    uvm_analysis_imp #({txn_type}, {cls.__name__}) {attr};")
                return
            if isinstance(value_node, ast.Call) and isinstance(value_node.func, ast.Attribute) and value_node.func.attr in ("uvm_config_db_set", "uvm_config_db_get"):
                return
            typ = _infer_sv_type(value_node)
            if typ:
                lines.append(f"    {typ} {attr};")

        # 扫描 __init__ 和各个 phase / body 中的 self.xxx
        for method_name in ("__init__", "build_phase", "connect_phase", "end_of_elaboration_phase", "run_phase", "body", "report_phase"):
            if not hasattr(cls, method_name):
                continue
            method = getattr(cls, method_name)
            try:
                src = inspect.getsource(method)
            except (TypeError, OSError):
                continue
            tree = ast.parse(textwrap.dedent(src))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                            _process_attr(tgt.attr, node.value)
                elif isinstance(node, ast.AugAssign):
                    tgt = node.target
                    if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                        if tgt.attr not in seen:
                            lines.append(f"    int {tgt.attr};")
                            seen.add(tgt.attr)
                # detect vif usage
                if isinstance(node, ast.Attribute):
                    base = self._expr_to_sv(node.value)
                    if base == "vif.cb" or base == "self.vif":
                        uses_vif = True

        # auto-declare vif for driver/monitor
        if uses_vif and if_name and issubclass(cls, (UVMDriver, UVMMonitor)) and "vif" not in seen:
            lines.append(f"    virtual {if_name} vif;")
            seen.add("vif")

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Method AST translator
    # -----------------------------------------------------------------
    def _translate_method(self, cls: Type[Any], method_name: str, skip_base: bool = False) -> Optional[str]:
        if not hasattr(cls, method_name):
            return None
        method = getattr(cls, method_name)
        if method_name in ("build_phase", "connect_phase", "run_phase", "body", "pre_body", "post_body") or skip_base:
            # 如果是基类默认实现，跳过
            defining_class = None
            for base in cls.__mro__:
                if method_name in base.__dict__:
                    defining_class = base
                    break
            if defining_class in (UVMComponent, UVMSequence, UVMSequenceItem, UVMDriver, UVMMonitor, UVMAgent, UVMEnv, UVMTest, UVMScoreboard, UVMSequencer):
                return None
        try:
            src = inspect.getsource(method)
        except (TypeError, OSError):
            return None
        src = textwrap.dedent(src)
        tree = ast.parse(src)
        func_def = tree.body[0]
        assert isinstance(func_def, (ast.FunctionDef, ast.AsyncFunctionDef))
        local_decls = self._collect_local_decls(cls, func_def)
        g = getattr(method, "__globals__", {})
        lines = []
        for stmt in func_def.body:
            sv = self._stmt_to_sv(stmt, globals_dict=g)
            if sv is not None:
                lines.append(sv)
        if not lines:
            return None
        if local_decls:
            lines = local_decls + lines
        return "\n".join(lines)

    def _collect_local_decls(self, cls: Type[Any], func_def: ast.FunctionDef) -> List[str]:
        decls: List[str] = []
        seen: Set[str] = set()
        prefix = self.indent * 2
        txn_type = self._resolve_txn_type(cls) or "uvm_sequence_item"
        for node in ast.walk(func_def):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id != "self" and tgt.id not in seen:
                        # skip list/dict initializations (will be declared inline)
                        if isinstance(node.value, (ast.List, ast.Dict)):
                            continue
                        # skip array repetition initializations like [0] * N
                        if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Mult) and isinstance(node.value.left, ast.List) and isinstance(node.value.right, ast.Constant):
                            continue
                        seen.add(tgt.id)
                        val = node.value
                        # await port.get() / peek() -> infer txn_type
                        if isinstance(val, ast.Await) and isinstance(val.value, ast.Call):
                            inner = val.value
                            if isinstance(inner.func, ast.Attribute) and inner.func.attr in ("get", "peek", "get_next_item"):
                                decls.append(f"{prefix}{txn_type} {tgt.id};")
                                continue
                        typ = self._infer_local_var_type(node.value, cls, txn_type)
                        if not typ:
                            typ = "int"
                        decls.append(f"{prefix}{typ} {tgt.id};")
        return decls

    def _infer_local_var_type(self, node: ast.AST, cls: Type[Any], txn_type: str) -> Optional[str]:
        if isinstance(node, ast.Attribute):
            # self.req or self.rsp in driver/sequence
            if isinstance(node.value, ast.Name) and node.value.id == "self" and node.attr in ("req", "rsp"):
                if issubclass(cls, UVMDriver):
                    return txn_type
                if issubclass(cls, UVMSequence):
                    return txn_type
        if not isinstance(node, ast.Call):
            return None
        func = node.func
        # create(Cls, name) -> Cls
        if isinstance(func, ast.Name) and func.id == "create":
            if node.args and isinstance(node.args[0], ast.Name):
                return node.args[0].id
        # SomeClass(...) -> SomeClass (only if it looks like a constructor/type)
        if isinstance(func, ast.Name):
            # heuristic: capitalized names are likely classes/types
            if func.id[0].isupper():
                return func.id
        if isinstance(func, ast.Attribute):
            if func.attr[0].isupper():
                return func.attr
        return None

    def _stmt_to_sv(self, node: ast.AST, indent: int = 2, globals_dict: Optional[Dict[str, Any]] = None) -> Optional[str]:
        prefix = self.indent * indent
        if isinstance(node, ast.Pass):
            return None
        if isinstance(node, ast.Expr):
            # skip coverage method calls
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                base_attr = self._expr_to_sv(node.value.func.value, globals_dict=globals_dict)
                attr_name = base_attr.split(".")[-1] if base_attr else ""
                if attr_name.startswith("cov_") and node.value.func.attr in ("sample", "report", "define_bins", "get_coverage"):
                    return None
            if isinstance(node.value, ast.Await):
                val = node.value.value
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "delay":
                    cycles = self._expr_to_sv(val.args[0], globals_dict=globals_dict) if val.args else "1"
                    if cycles == "1":
                        return f"{prefix}@vif.cb;"
                    return f"{prefix}repeat ({cycles}) @vif.cb;"
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id in ("uvm_do", "uvm_do_with"):
                    sv = self._call_to_sv(val, globals_dict=globals_dict)
                    return f"{prefix}{sv}" if sv else None
                sv = self._expr_to_sv(val, globals_dict=globals_dict)
                return f"{prefix}{sv};" if sv else None
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id in ("uvm_do", "uvm_do_with"):
                sv = self._call_to_sv(node.value, globals_dict=globals_dict)
                return f"{prefix}{sv}" if sv else None
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "assert_eq":
                args = [self._expr_to_sv(a, globals_dict=globals_dict) for a in node.value.args]
                if len(args) >= 2:
                    msg = args[2] if len(args) > 2 else '"assertion failed"'
                    return f"{prefix}assert ({args[0]} == {args[1]}) else `uvm_error(\"CHECKER\", {msg});"
                return None
            # suppress calls to internal Python methods (e.g. self._check) that have no SV counterpart
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                base = self._expr_to_sv(node.value.func.value, globals_dict=globals_dict)
                if base == "this" and node.value.func.attr.startswith("_"):
                    return f"{prefix}// omitted: this.{node.value.func.attr}(...)"
            expr = self._expr_to_sv(node.value, globals_dict=globals_dict)
            if expr:
                expr = expr.rstrip(';')
                return f"{prefix}{expr};"
            return None
        if isinstance(node, ast.Await):
            val = node.value
            # await delay(cycles)
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "delay":
                cycles = self._expr_to_sv(val.args[0], globals_dict=globals_dict) if val.args else "1"
                if cycles == "1":
                    return f"{prefix}@vif.cb;"
                return f"{prefix}repeat ({cycles}) @vif.cb;"
            # await uvm_do(item) / uvm_do_with -> 对应 SV macro
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id in ("uvm_do", "uvm_do_with"):
                sv = self._call_to_sv(val, globals_dict=globals_dict)
                return f"{prefix}{sv}" if sv else None
            # 其他 await 直接去掉 await（SV task 调用本身就是阻塞的）
            sv = self._expr_to_sv(val, globals_dict=globals_dict)
            if sv:
                sv = sv.rstrip(';')
                return f"{prefix}{sv};"
            return None
        if isinstance(node, ast.Assign):
            # skip coverage instantiation
            if isinstance(node.value, ast.Call):
                func = node.value.func
                if isinstance(func, ast.Name) and func.id == "Coverage":
                    return None
            # array element assignment: arr[idx] = val
            if isinstance(node.targets[0], ast.Subscript):
                arr = self._expr_to_sv(node.targets[0].value, globals_dict=globals_dict)
                idx = self._expr_to_sv(node.targets[0].slice, globals_dict=globals_dict)
                val = self._expr_to_sv(node.value, globals_dict=globals_dict)
                if arr and idx and val:
                    return f"{prefix}{arr}[{idx}] = {val};"
                return None
            # array declaration from repetition: [x] * N
            if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Mult) and isinstance(node.value.left, ast.List) and isinstance(node.value.right, ast.Constant):
                lhs = self._expr_to_sv(node.targets[0], globals_dict=globals_dict)
                n = node.value.right.value
                elem_nodes = node.value.left.elts
                if len(elem_nodes) == 1:
                    elem_sv = self._expr_to_sv(elem_nodes[0], globals_dict=globals_dict)
                    if lhs and elem_sv is not None:
                        init = ", ".join([elem_sv] * n)
                        return f"{prefix}longint {lhs} [{n}] = '{{{init}}};"
                elif len(elem_nodes) == n:
                    elems = [self._expr_to_sv(e, globals_dict=globals_dict) for e in elem_nodes]
                    if lhs and all(elems):
                        init = ", ".join(elems)
                        return f"{prefix}longint {lhs} [{n}] = '{{{init}}};"
            # local list declaration -> SV array
            if isinstance(node.value, ast.List):
                lhs = self._expr_to_sv(node.targets[0], globals_dict=globals_dict)
                elems = [self._expr_to_sv(e, globals_dict=globals_dict) for e in node.value.elts]
                if lhs and all(elems):
                    if elems and all(isinstance(e, str) and e.startswith('"') for e in elems):
                        size = len(elems)
                        init = ", ".join(elems)
                        return f'{prefix}string {lhs} [{size}] = \'{{{init}}};'
                    vals = []
                    max_int = 0
                    for e in elems:
                        s = str(e)
                        if s.startswith('0x') or s.startswith('0X'):
                            v = int(s, 16)
                        else:
                            try:
                                v = int(s)
                            except ValueError:
                                v = 0
                        vals.append(v)
                        if v > max_int:
                            max_int = v
                    width = max_int.bit_length()
                    width = max(width, 1)
                    width_str = f"[{width-1}:0] " if width > 1 else ""
                    size = len(elems)
                    init = ", ".join(str(e) for e in elems)
                    return f"{prefix}logic {width_str}{lhs} [{size}] = '{{{init}}};"
            # 过滤 config db 赋值（支持 total = self.cfg_db_get("key") or 0）
            cfg_db_node = None
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr in ("uvm_config_db_set", "uvm_config_db_get", "cfg_db_set", "cfg_db_get"):
                cfg_db_node = node.value
            elif isinstance(node.value, ast.BoolOp) and len(node.value.values) >= 1 and isinstance(node.value.values[0], ast.Call) and isinstance(node.value.values[0].func, ast.Attribute) and node.value.values[0].func.attr in ("cfg_db_get", "uvm_config_db_get"):
                cfg_db_node = node.value.values[0]
            if cfg_db_node:
                return self._config_db_assign_to_sv(prefix, node.targets[0], cfg_db_node, globals_dict)
            # self.xxx = SomeClass("name", self) 或 local xxx = SomeClass("name", self) -> create
            if self._is_create_call(node.value, globals_dict=globals_dict):
                sv = self._create_call_to_sv(node.targets[0], node.value)
                if sv:
                    return f"{prefix}{sv};"
            # await get_next_item / get / peek 赋值: lhs = await port.get() -> port.get(lhs);
            if isinstance(node.value, ast.Await):
                inner = node.value.value
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and inner.func.attr in ("get_next_item", "get", "peek"):
                    lhs = self._expr_to_sv(node.targets[0], globals_dict=globals_dict)
                    base = self._expr_to_sv(inner.func.value, globals_dict=globals_dict)
                    # rewrite UVMBlockingGetPort.get -> fifo.get (but not seq_item_port)
                    if base and base.endswith("_port") and not base.endswith(".seq_item_port"):
                        base = base[: -len("_port")] + "_fifo"
                    if lhs and base:
                        return f"{prefix}{base}.{inner.func.attr}({lhs});"
                lhs = self._expr_to_sv(node.targets[0], globals_dict=globals_dict)
                rhs = self._expr_to_sv(node.value, globals_dict=globals_dict)
                if lhs and rhs:
                    if "vif.cb." in lhs:
                        return f"{prefix}{lhs} <= {rhs};"
                    return f"{prefix}{lhs} = {rhs};"
                return None
            # 普通赋值
            lhs = self._expr_to_sv(node.targets[0], globals_dict=globals_dict)
            rhs = self._expr_to_sv(node.value, globals_dict=globals_dict)
            if lhs and rhs:
                # vif.cb.xxx = value -> vif.cb.xxx <= value
                if "vif.cb." in lhs:
                    return f"{prefix}{lhs} <= {rhs};"
                return f"{prefix}{lhs} = {rhs};"
            return None
        if isinstance(node, ast.AugAssign):
            lhs = self._expr_to_sv(node.target, globals_dict=globals_dict)
            rhs = self._expr_to_sv(node.value, globals_dict=globals_dict)
            op = self._op_to_sv(node.op)
            if lhs and rhs and op:
                return f"{prefix}{lhs} {op}= {rhs};"
            return None
        if isinstance(node, ast.If):
            cond = self._expr_to_sv(node.test, globals_dict=globals_dict)
            lines = [f"{prefix}if ({cond}) begin"]
            for s in node.body:
                sv = self._stmt_to_sv(s, indent + 1, globals_dict=globals_dict)
                if sv: lines.append(sv)
            if node.orelse:
                lines.append(f"{prefix}end else begin")
                for s in node.orelse:
                    sv = self._stmt_to_sv(s, indent + 1, globals_dict=globals_dict)
                    if sv: lines.append(sv)
            lines.append(f"{prefix}end")
            return "\n".join(lines)
        if isinstance(node, ast.While):
            cond = self._expr_to_sv(node.test, globals_dict=globals_dict)
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                lines = [f"{prefix}forever begin"]
            else:
                lines = [f"{prefix}while ({cond}) begin"]
            for s in node.body:
                sv = self._stmt_to_sv(s, indent + 1, globals_dict=globals_dict)
                if sv: lines.append(sv)
            lines.append(f"{prefix}end")
            return "\n".join(lines)
        if isinstance(node, ast.For):
            # for _ in repeat(N): -> repeat (N) begin
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "repeat":
                count = self._expr_to_sv(node.iter.args[0], globals_dict=globals_dict)
                lines = [f"{prefix}repeat ({count}) begin"]
                for s in node.body:
                    sv = self._stmt_to_sv(s, indent + 1, globals_dict=globals_dict)
                    if sv: lines.append(sv)
                lines.append(f"{prefix}end")
                return "\n".join(lines)
            # for i in range(a, b): -> for (int i = a; i < b; i++) begin
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                var = node.target.id if isinstance(node.target, ast.Name) else "i"
                args = [self._expr_to_sv(a, globals_dict=globals_dict) for a in node.iter.args]
                if len(args) == 0:
                    start = "0"; end = "0"
                elif len(args) == 1:
                    start = "0"; end = args[0]
                else:
                    start = args[0]; end = args[1]
                lines = [f"{prefix}for (int {var} = {start}; {var} < {end}; {var} = {var} + 1) begin"]
                for s in node.body:
                    sv = self._stmt_to_sv(s, indent + 1, globals_dict=globals_dict)
                    if sv: lines.append(sv)
                lines.append(f"{prefix}end")
                return "\n".join(lines)
            # for a in my_list: -> foreach (my_list[{a}_idx]) ...
            if isinstance(node.iter, ast.Name):
                var = node.target.id if isinstance(node.target, ast.Name) else "i"
                arr = node.iter.id
                lines = [f"{prefix}for (int {var}_idx = 0; {var}_idx < $size({arr}); {var}_idx = {var}_idx + 1) begin"]
                lines.append(f"{prefix}    automatic var {var} = {arr}[{var}_idx];")
                for s in node.body:
                    sv = self._stmt_to_sv(s, indent + 1, globals_dict=globals_dict)
                    if sv: lines.append(sv)
                lines.append(f"{prefix}end")
                return "\n".join(lines)
            return f"{prefix}// Unsupported for-loop"
        if isinstance(node, ast.Return):
            if node.value:
                return f"{prefix}return {self._expr_to_sv(node.value, globals_dict=globals_dict)};"
            return f"{prefix}return;"
        if isinstance(node, ast.Raise):
            # raise uvm_fatal(id, msg) -> `uvm_fatal(id, msg)
            if isinstance(node.exc, ast.Call):
                func = node.exc.func
                if isinstance(func, ast.Name) and func.id in ("uvm_fatal", "uvm_error", "uvm_warning"):
                    args = ", ".join(self._expr_to_sv(a, globals_dict=globals_dict) for a in node.exc.args)
                    return f"{prefix}`{func.id}({args})"
            return f"{prefix}// raise statement not translated"
        return f"{prefix}// unhandled Python statement: {ast.dump(node)}"

    def _config_db_assign_to_sv(self, prefix: str, target: ast.AST, node: ast.Call, globals_dict: Optional[Dict[str, Any]] = None) -> Optional[str]:
        attr = node.func.attr
        args = node.args
        if len(args) < 1:
            return None
        key = self._expr_to_sv(args[0], globals_dict=globals_dict)
        if attr in ("uvm_config_db_set", "cfg_db_set"):
            if len(args) < 2:
                return None
            val = self._expr_to_sv(args[1], globals_dict=globals_dict)
            if key == '"vif"':
                return f"{prefix}uvm_config_db#(virtual fp8_alu_if)::set(this, \"\", {key}, {val})"
            return f"{prefix}uvm_config_db#(int)::set(this, \"\", {key}, {val})"
        if attr in ("cfg_db_get", "uvm_config_db_get"):
            lhs = self._expr_to_sv(target, globals_dict=globals_dict)
            if lhs:
                return f'{prefix}if (!uvm_config_db#(int)::get(this, "", {key}, {lhs}))\n{prefix}    {lhs} = 0;'
            return None

    def _expr_to_sv(self, node: ast.AST, globals_dict: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return f'"{node.value}"'
            if isinstance(node.value, bool):
                return "1'b1" if node.value else "1'b0"
            if node.value is None:
                return "null"
            return str(node.value)
        if isinstance(node, ast.Name):
            mapping = {"self": "this", "True": "1'b1", "False": "1'b0", "None": "null"}
            return mapping.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            base = self._expr_to_sv(node.value, globals_dict=globals_dict)
            if base == "self":
                return node.attr
            if base and base.endswith(".cb"):
                return f"{base}.{node.attr}"
            if base:
                return f"{base}.{node.attr}"
            return node.attr
        if isinstance(node, ast.BinOp):
            l = self._expr_to_sv(node.left, globals_dict=globals_dict)
            r = self._expr_to_sv(node.right, globals_dict=globals_dict)
            op = self._op_to_sv(node.op)
            if l and r and op:
                return f"({l} {op} {r})"
            return None
        if isinstance(node, ast.UnaryOp):
            op = self._op_to_sv(node.op)
            v = self._expr_to_sv(node.operand, globals_dict=globals_dict)
            if op and v:
                return f"({op}{v})"
            return None
        if isinstance(node, ast.BoolOp):
            vals = [self._expr_to_sv(v, globals_dict=globals_dict) for v in node.values]
            if isinstance(node.op, ast.And):
                vals = [v for v in vals if v and v != "null"]
                if not vals:
                    return "1'b1"
                return " && ".join(f"({v})" for v in vals)
            else:  # Or
                vals = [v for v in vals if v and v != "null"]
                if not vals:
                    return "0"
                return " || ".join(f"({v})" for v in vals)
        if isinstance(node, ast.Compare):
            left = self._expr_to_sv(node.left, globals_dict=globals_dict)
            parts = [left] if left else []
            for op_node, comparator in zip(node.ops, node.comparators):
                op = self._cmp_op_to_sv(op_node)
                right = self._expr_to_sv(comparator, globals_dict=globals_dict)
                if op and right:
                    parts.append(f"{op} {right}")
            return " ".join(parts)
        if isinstance(node, ast.Call):
            return self._call_to_sv(node, globals_dict=globals_dict)
        if isinstance(node, ast.Subscript):
            base = self._expr_to_sv(node.value, globals_dict=globals_dict)
            idx = self._expr_to_sv(node.slice, globals_dict=globals_dict)
            if base and idx:
                return f"{base}[{idx}]"
            return None
        if isinstance(node, ast.JoinedStr):
            format_parts = []
            args = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    format_parts.append(v.value.replace("%", "%%"))
                elif isinstance(v, ast.FormattedValue):
                    format_parts.append("%0d")
                    arg_sv = self._expr_to_sv(v.value, globals_dict=globals_dict)
                    if arg_sv:
                        args.append(arg_sv)
            fmt = "".join(format_parts)
            return f'$sformatf("{fmt}", {", ".join(args)})'
        return None

    def _call_to_sv(self, node: ast.Call, globals_dict: Optional[Dict[str, Any]] = None) -> Optional[str]:
        func = node.func
        args = [self._expr_to_sv(a, globals_dict=globals_dict) for a in node.args]
        # len(x) -> evaluate if possible
        if isinstance(func, ast.Name) and func.id == "len" and node.args:
            arg_node = node.args[0]
            if isinstance(arg_node, ast.Name) and globals_dict:
                val = globals_dict.get(arg_node.id)
                if val is not None and hasattr(val, '__len__'):
                    return str(len(val))
        # create(cls, name) -> Cls::type_id::create(name)
        if isinstance(func, ast.Name) and func.id == "create" and len(args) >= 2:
            cls_name = args[0]
            name_arg = args[1]
            return f"{cls_name}::type_id::create({name_arg})"
        # delay(cycles) -> @vif.cb; 或 #1
        if isinstance(func, ast.Name) and func.id == "delay":
            return "@vif.cb"
        # start_item / finish_item / randomize / uvm_info 等直接保留
        if isinstance(func, ast.Name) and func.id == "int":
            return args[0] if args else None
        if isinstance(func, ast.Name) and func.id == "print":
            return f"$display({', '.join(a for a in args if a)})"
        if isinstance(func, ast.Name) and func.id == "UVMAnalysisFIFO":
            name_arg = args[0] if args else '"fifo"'
            return f"new({name_arg}, this)"
        if isinstance(func, ast.Name) and func.id == "uvm_do_with":
            if len(node.args) >= 1:
                item_sv = self._expr_to_sv(node.args[0], globals_dict=globals_dict)
                constraints_sv = ""
                if len(node.args) >= 2:
                    constraints_sv = self._uvm_do_with_constraints(node.args[1])
                if constraints_sv:
                    return f"`uvm_do_with({item_sv}, {{{constraints_sv}}})"
                return f"`uvm_do_with({item_sv})"
            return None
        if isinstance(func, ast.Name) and func.id in ("start_item", "finish_item", "randomize", "uvm_info", "uvm_warning", "uvm_fatal"):
            return f"{func.id}({', '.join(a for a in args if a)})"
        # super().__init__(name, parent) -> super.new(name, parent)
        if isinstance(func, ast.Attribute) and func.attr == "__init__":
            if isinstance(func.value, ast.Call) and isinstance(func.value.func, ast.Name) and func.value.func.id == "super":
                aargs = [a if a != "self" else "this" for a in args]
                return f"super.new({', '.join(aargs)})"
        # phase.raise_objection(self) -> phase.raise_objection(this)
        if isinstance(func, ast.Attribute) and func.attr == "raise_objection":
            base = self._expr_to_sv(func.value, globals_dict=globals_dict)
            aargs = [a if a != "self" else "this" for a in args]
            return f"{base}.raise_objection({', '.join(aargs)})"
        if isinstance(func, ast.Attribute) and func.attr == "drop_objection":
            base = self._expr_to_sv(func.value, globals_dict=globals_dict)
            aargs = [a if a != "self" else "this" for a in args]
            return f"{base}.drop_objection({', '.join(aargs)})"
        # cfg_db_set / cfg_db_get / uvm_config_db_set / uvm_config_db_get
        if isinstance(func, ast.Attribute) and func.attr in ("cfg_db_set", "uvm_config_db_set"):
            if len(node.args) >= 2:
                key = args[0]
                val = args[1]
                if key == '"vif"':
                    return f"uvm_config_db#(virtual fp8_alu_if)::set(this, \"\", {key}, {val})"
                return f"uvm_config_db#(int)::set(this, \"\", {key}, {val})"
            return None
        if isinstance(func, ast.Attribute) and func.attr in ("cfg_db_get", "uvm_config_db_get"):
            return "null"
        # connect_export / connect_get_port 映射
        if isinstance(func, ast.Attribute) and func.attr == "connect_export":
            base = self._expr_to_sv(func.value, globals_dict=globals_dict)
            aargs = [a if a != "self" else "this" for a in args]
            return f"{base}.analysis_export.connect({', '.join(aargs)});"
        if isinstance(func, ast.Attribute) and func.attr == "connect_get_port":
            return ""
        # self.seq_item_port.get_next_item(self.req) -> seq_item_port.get_next_item(req)
        if isinstance(func, ast.Attribute) and func.attr in ("get_next_item", "item_done", "write", "connect", "start"):
            base = self._expr_to_sv(func.value, globals_dict=globals_dict)
            aargs = [a if a != "self" else "this" for a in args]
            return f"{base}.{func.attr}({', '.join(aargs)})"
        # UVMBlockingGetPort.get -> rewrite to fifo.get
        if isinstance(func, ast.Attribute) and func.attr in ("get", "peek", "try_get"):
            base = self._expr_to_sv(func.value, globals_dict=globals_dict)
            if base and base.endswith("_port"):
                base = base[: -len("_port")] + "_fifo"
            aargs = [a if a != "self" else "this" for a in args]
            return f"{base}.{func.attr}({', '.join(aargs)})"
        # self.xxx = SomeClass(...) 已经在 stmt 层处理，这里是普通函数调用
        if isinstance(func, ast.Name):
            # check for sv_dpi reference model functions
            if globals_dict:
                ref = globals_dict.get(func.id)
                if callable(ref) and getattr(ref, "_sv_dpi", None):
                    return f"{func.id}({', '.join(a for a in args if a)})"
            return f"{func.id}({', '.join(a for a in args if a)})"
        if isinstance(func, ast.Attribute):
            base = self._expr_to_sv(func.value, globals_dict=globals_dict)
            return f"{base}.{func.attr}({', '.join(a for a in args if a)})"
        return None

    def _uvm_do_with_constraints(self, node: ast.AST) -> str:
        """将 Python 的 constraints 参数转译为 SV inline constraints 字符串。"""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # 直接是约束字符串
            return node.value.strip()
        if isinstance(node, ast.Dict):
            parts = []
            for k_node, v_node in zip(node.keys, node.values):
                key = self._expr_to_sv(k_node)
                if key is None:
                    continue
                if isinstance(v_node, ast.Constant):
                    if isinstance(v_node.value, str):
                        # 字符串直接嵌入，如 "< 10" -> "count < 10;"
                        parts.append(f"{key} {v_node.value.strip()};")
                    elif isinstance(v_node.value, bool):
                        val = "1'b1" if v_node.value else "1'b0"
                        parts.append(f"{key} == {val};")
                    else:
                        parts.append(f"{key} == {v_node.value};")
                else:
                    val = self._expr_to_sv(v_node)
                    if val:
                        parts.append(f"{key} == {val};")
            return " ".join(parts)
        if isinstance(node, ast.Name):
            # 可能是变量，生成占位符（SV 编译时需要用户手动替换）
            return f"/* constraints: {node.id} */"
        return ""

    def _is_create_call(self, node: ast.AST, globals_dict: Optional[Dict[str, Any]] = None) -> bool:
        """判断是否是 self.xxx = SomeClass('name', self) 的实例化。"""
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        if isinstance(func, ast.Name):
            if func.id in ("UVMSequencer", "UVMDriver", "UVMMonitor", "UVMAgent", "UVMEnv", "UVMScoreboard", "UVMSequence", "UVMAnalysisImp"):
                return True
            if globals_dict:
                ref = globals_dict.get(func.id)
                if isinstance(ref, type) and issubclass(ref, (UVMComponent, UVMSequenceItem)):
                    return True
        if isinstance(func, ast.Attribute):
            if func.attr in ("UVMSequencer", "UVMDriver", "UVMMonitor", "UVMAgent", "UVMEnv", "UVMScoreboard", "UVMSequence", "UVMAnalysisImp"):
                return True
            if globals_dict:
                ref = globals_dict.get(func.attr)
                if isinstance(ref, type) and issubclass(ref, (UVMComponent, UVMSequenceItem)):
                    return True
        return False

    def _create_call_to_sv(self, target: ast.AST, node: ast.Call) -> Optional[str]:
        var = None
        if isinstance(target, ast.Attribute):
            var = target.attr
        elif isinstance(target, ast.Name):
            var = target.id
        if var is None:
            return None
        func = node.func
        cls_name = func.id if isinstance(func, ast.Name) else func.attr
        # 提取 name 参数（第一个字符串参数）
        name_arg = f'"{var}"'
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                name_arg = f'"{arg.value}"'
                break
        return f"{var} = {cls_name}::type_id::create({name_arg}, this)"

    def _op_to_sv(self, op: ast.operator) -> Optional[str]:
        mapping = {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
            ast.Mod: "%", ast.Pow: "**", ast.LShift: "<<", ast.RShift: ">>",
            ast.BitOr: "|", ast.BitXor: "^", ast.BitAnd: "&",
            ast.And: "&&", ast.Or: "||",
            ast.Invert: "~", ast.Not: "!",
            ast.UAdd: "+", ast.USub: "-",
        }
        return mapping.get(type(op))

    def _cmp_op_to_sv(self, op: ast.cmpop) -> Optional[str]:
        mapping = {
            ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
            ast.Gt: ">", ast.GtE: ">=", ast.Is: "==", ast.IsNot: "!=",
        }
        return mapping.get(type(op))

    # -----------------------------------------------------------------
    # Package / Interface / TB top
    # -----------------------------------------------------------------
    def _emit_pkg(self, pkg_name: str, all_classes: Dict[str, List[Type[Any]]]) -> str:
        header = self._file_header(f"{pkg_name}.sv", pkg_name)
        includes: List[str] = []
        for txn_cls in all_classes["transactions"]:
            includes.append(f'    `include "{txn_cls.__name__}.sv"')
        for comp_cls in all_classes["components"]:
            includes.append(f'    `include "{self._to_snake(comp_cls.__name__)}.sv"')
        includes_str = "\n".join(includes)
        return f"""{header}package {pkg_name};
    import uvm_pkg::*;
    `include "uvm_macros.svh"

{includes_str}
endpackage : {pkg_name}
"""

    @staticmethod
    def _to_sv_width(width: int) -> str:
        return f"[{width - 1}:0] " if width > 1 else ""

    def _find_clock(self, module: Module) -> Optional[str]:
        for n in ["clk", "clock", "aclk", "pclk"]:
            if n in module._inputs:
                return n
        return None

    def _emit_interface(self, module: Module, if_name: str, clk: Optional[str], vif_extra: Optional[Set[str]] = None) -> str:
        clk = clk or "clk"
        vif_extra = vif_extra or set()
        lines = [f"interface {if_name} (input logic {clk});", ""]
        for n, s in module._inputs.items():
            if n == clk:
                continue
            lines.append(f"    logic {self._to_sv_width(s.width)}{n};")
        for n, s in module._outputs.items():
            lines.append(f"    logic {self._to_sv_width(s.width)}{n};")
        for sig in sorted(vif_extra):
            # skip DUT ports that are already declared
            if sig in module._inputs or sig in module._outputs or sig == clk:
                continue
            lines.append(f"    logic {sig};")
        lines.append("")
        # clocking block（数据端口）
        ignore = {clk, "rst", "reset", "rst_n", "reset_n", "aresetn", "presetn"}
        lines.append(f"    clocking cb @(posedge {clk});")
        for n, s in module._inputs.items():
            if n in ignore:
                continue
            lines.append(f"        output {self._to_sv_width(s.width)}{n};")
        for n, s in module._outputs.items():
            lines.append(f"        input  {self._to_sv_width(s.width)}{n};")
        for sig in sorted(vif_extra):
            if sig in ignore or sig == clk:
                continue
            lines.append(f"        inout  {sig};")
        lines.append("    endclocking")
        lines.append("")
        lines.append("    modport MP (clocking cb);")
        lines.append(f"endinterface : {if_name}")
        lines.append("")
        return "\n".join(lines)

    def _emit_tb_top(self, module: Module, test_name: str, if_name: str, clk: Optional[str]) -> str:
        clk = clk or "clk"
        rst_name = ""
        rst_active_low = False
        for r in ["rst_n", "reset_n", "aresetn", "rst", "reset"]:
            if r in module._inputs:
                rst_name = r
                rst_active_low = r.endswith("_n") or r.startswith("aresetn")
                break
        rst_wire = f"    logic {rst_name};\n" if rst_name else ""
        rst_init = f"        {rst_name} = {'1\'b0' if rst_active_low else '1\'b1'};\n"
        rst_release = f"        {rst_name} = {'1\'b1' if rst_active_low else '1\'b0'};\n"
        port_conns = []
        for n in module._inputs:
            if n == clk:
                port_conns.append(f"        .{n}(vif.{n}),")
            elif n == rst_name:
                port_conns.append(f"        .{n}({rst_name}),")
            else:
                port_conns.append(f"        .{n}(vif.{n}),")
        for n in module._outputs:
            port_conns.append(f"        .{n}(vif.{n}),")
        port_conns_str = "\n".join(port_conns).rstrip(",")
        rst_block = f"""    initial begin
{rst_init}        repeat (5) @(posedge {clk});
{rst_release}    end
""" if rst_name else ""
        body = f"""`timescale 1ns/1ps

module tb_top;

    logic {clk};
{rst_wire}    {if_name} vif (.{clk}({clk}));

    {module.name} dut (
{port_conns_str}
    );

    initial begin
        uvm_config_db # (virtual {if_name})::set(null, "*", "vif", vif);
        run_test("{test_name}");
    end

{rst_block}
    initial begin
        {clk} = 0;
        forever #5 {clk} = ~{clk};
    end

endmodule
"""
        return body.replace("{{rstr}}", rst_block)

    def _to_snake(self, name: str) -> str:
        s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
