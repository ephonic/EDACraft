"""File operation tools: read, write, edit."""

from __future__ import annotations

import asyncio
import json
import os
import re
from difflib import unified_diff
from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import BaseTool, ToolProgress, ToolResult, ValidationResult


class FileReadTool(BaseTool):
    """Read the contents of a file."""

    name = "file_read"
    aliases = ["read", "cat", "view"]
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file to read.",
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (1-indexed). Use negative values to read from end.",
                "default": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read. Default 1000.",
                "default": 1000,
            },
        },
        "required": ["path"],
    }
    is_read_only = True

    def description(self) -> str:
        return "Read the contents of a file. Supports reading specific line ranges."

    def validate_input(self, args: Dict[str, Any], context: Any) -> ValidationResult:
        path = args.get("path")
        if not path or not isinstance(path, str) or not path.strip():
            return ValidationResult(
                result=False,
                message="Missing required parameter 'path'. Example: {'path': '/home/user/design.py'}. NEVER call file_read with empty {} or without 'path'.",
            )
        return ValidationResult(result=True)

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        path = args["path"]
        offset = args.get("offset", 1)
        limit = args.get("limit", 1000)

        if not os.path.isabs(path):
            # Resolve relative to project root if available
            root = getattr(context, "project_root", os.getcwd())
            path = os.path.join(root, path)

        if not os.path.exists(path):
            return ToolResult(data={"error": f"File not found: {path}"})

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return ToolResult(data={"error": str(e)})

        total_lines = len(lines)

        if offset < 0:
            offset = max(1, total_lines + offset + 1)

        start = max(0, offset - 1)
        end = min(total_lines, start + limit)
        selected = lines[start:end]

        content = "".join(selected)
        return ToolResult(data={
            "path": path,
            "content": content,
            "total_lines": total_lines,
            "start_line": start + 1,
            "end_line": end,
        })


class FileWriteTool(BaseTool):
    """Write content to a file (create or overwrite)."""

    name = "file_write"
    aliases = ["write", "create_file", "file_creator"]
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "REQUIRED. Absolute or relative path to the file to write. MUST be non-empty. NEVER omit.",
            },
            "content": {
                "type": "string",
                "description": "REQUIRED. Content to write to the file. MUST be a string. NEVER omit.",
            },
            "append": {
                "type": "boolean",
                "description": "If true, append to the file instead of overwriting.",
                "default": False,
            },
        },
        "required": ["path", "content"],
    }
    is_destructive = True

    def description(self) -> str:
        return "Write content to a file. Creates the file if it doesn't exist, overwrites by default."

    def validate_input(self, args: Dict[str, Any], context: Any) -> ValidationResult:
        path = args.get("path")
        content = args.get("content")
        if not path or not isinstance(path, str) or not path.strip():
            return ValidationResult(
                result=False,
                message=f"Missing required parameter 'path'. You sent: {json.dumps(args, ensure_ascii=False)}. Example: {{'path': '/home/user/design.py', 'content': '...'}}. NEVER call file_write with empty {{}} or without 'path'.",
            )
        if content is None or not isinstance(content, str):
            return ValidationResult(
                result=False,
                message=f"Missing required parameter 'content'. You sent: {json.dumps(args, ensure_ascii=False)}. Example: {{'path': '/home/user/design.py', 'content': '...'}}. NEVER call file_write without 'content'.",
            )
        return ValidationResult(result=True)

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        path = args.get("path")
        content = args.get("content")
        if path is None or content is None:
            return ToolResult(data={
                "error": (
                    "Missing required parameters for file_write. "
                    "You MUST provide: 'path' (file path) and 'content' (file content). "
                    "Example: {'path': '/home/user/design.py', 'content': 'import pyAether...'}"
                ),
            })
        append = args.get("append", False)

        if not os.path.isabs(path):
            root = getattr(context, "project_root", os.getcwd())
            path = os.path.join(root, path)

        def _do_write():
            dir_name = os.path.dirname(path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            mode = "a" if append else "w"
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)
            return {"path": path, "status": "written", "bytes": len(content.encode("utf-8"))}

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _do_write)
            return ToolResult(data=result)
        except Exception as e:
            return ToolResult(data={"error": f"file_write failed: {e}"})


class FileEditTool(BaseTool):
    """Edit a file by replacing specific text strings."""

    name = "file_edit"
    aliases = ["edit", "replace", "str_replace"]
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to edit.",
            },
            "old_string": {
                "type": "string",
                "description": "The exact text to replace. Must match uniquely in the file.",
            },
            "new_string": {
                "type": "string",
                "description": "The replacement text.",
            },
        },
        "required": ["path", "old_string", "new_string"],
    }
    is_destructive = True

    def description(self) -> str:
        return "Edit a file by replacing a unique string with another. Use read first to see the content."

    def validate_input(self, args: Dict[str, Any], context: Any) -> ValidationResult:
        path = args.get("path")
        old_string = args.get("old_string")
        new_string = args.get("new_string")
        if not path or not isinstance(path, str) or not path.strip():
            return ValidationResult(
                result=False,
                message="Missing required parameter 'path'. Example: {'path': '/home/user/design.py', 'old_string': 'foo', 'new_string': 'bar'}. NEVER call file_edit without 'path'.",
            )
        if old_string is None or not isinstance(old_string, str):
            return ValidationResult(
                result=False,
                message="Missing required parameter 'old_string'. Example: {'path': '...', 'old_string': 'foo', 'new_string': 'bar'}. NEVER call file_edit without 'old_string'.",
            )
        if new_string is None or not isinstance(new_string, str):
            return ValidationResult(
                result=False,
                message="Missing required parameter 'new_string'. Example: {'path': '...', 'old_string': 'foo', 'new_string': 'bar'}. NEVER call file_edit without 'new_string'.",
            )
        return ValidationResult(result=True)

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        path = args["path"]
        old_string = args["old_string"]
        new_string = args["new_string"]

        if not os.path.isabs(path):
            root = getattr(context, "project_root", os.getcwd())
            path = os.path.join(root, path)

        if not os.path.exists(path):
            return ToolResult(data={"error": f"File not found: {path}"})

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return ToolResult(data={"error": str(e)})

        occurrences = content.count(old_string)
        if occurrences == 0:
            return ToolResult(data={"error": f"String not found in file: {old_string[:50]}..."})
        if occurrences > 1:
            return ToolResult(data={"error": f"String found {occurrences} times. Must be unique for safe replacement."})

        new_content = content.replace(old_string, new_string, 1)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception as e:
            return ToolResult(data={"error": str(e)})

        # Generate diff preview
        old_lines = content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = list(unified_diff(old_lines, new_lines, fromfile=path, tofile=path, lineterm=""))
        diff_str = "".join(diff[:50])  # Limit diff size

        return ToolResult(data={
            "path": path,
            "status": "edited",
            "replacements": 1,
            "diff_preview": diff_str,
        })


class GlobTool(BaseTool):
    """Find files matching a glob pattern."""

    name = "glob"
    aliases = ["find_files", "list_files"]
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "REQUIRED. Glob pattern to match files. E.g., '*.py', 'src/**/*.v'. MUST be non-empty. NEVER omit.",
            },
            "directory": {
                "type": "string",
                "description": "Directory to search in. Defaults to project root.",
            },
        },
        "required": ["pattern"],
    }
    is_read_only = True

    def description(self) -> str:
        return "Find files matching a glob pattern. Use '**' for recursive search."

    def validate_input(self, args: Dict[str, Any], context: Any) -> ValidationResult:
        pattern = args.get("pattern")
        if not pattern or not isinstance(pattern, str) or not pattern.strip():
            return ValidationResult(
                result=False,
                message="Missing required parameter 'pattern'. Example: {'pattern': 'src/**/*.py', 'directory': '/home/user/project'}. NEVER call glob with empty {} or without 'pattern'."
            )
        return ValidationResult(result=True)

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        import glob as glob_module

        pattern = args["pattern"]
        directory = args.get("directory", getattr(context, "project_root", os.getcwd()))

        if not os.path.isabs(directory):
            directory = os.path.join(os.getcwd(), directory)

        search_path = os.path.join(directory, pattern)
        matches = glob_module.glob(search_path, recursive=True)

        # Relative paths for cleaner output
        rel_matches = [os.path.relpath(m, directory) for m in matches]
        rel_matches.sort()

        return ToolResult(data={
            "pattern": pattern,
            "directory": directory,
            "matches": rel_matches,
            "count": len(rel_matches),
        })


class GrepTool(BaseTool):
    """Search for text patterns in files using regex."""

    name = "grep"
    aliases = ["search", "rg", "find_text"]
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "REQUIRED. Regex pattern to search for. MUST be non-empty. NEVER omit.",
            },
            "path": {
                "type": "string",
                "description": "REQUIRED. File or directory to search in. MUST be non-empty. NEVER omit.",
            },
            "glob": {
                "type": "string",
                "description": "Optional glob filter for files when searching a directory.",
            },
            "output_mode": {
                "type": "string",
                "enum": ["content", "files_with_matches", "count_matches"],
                "description": "Output format. Default: content.",
                "default": "content",
            },
        },
        "required": ["pattern", "path"],
    }
    is_read_only = True

    def description(self) -> str:
        return "Search for regex patterns in files. Supports file and directory search."

    def validate_input(self, args: Dict[str, Any], context: Any) -> ValidationResult:
        pattern = args.get("pattern")
        path = args.get("path")
        if not pattern or not isinstance(pattern, str) or not pattern.strip():
            return ValidationResult(
                result=False,
                message="Missing required parameter 'pattern'. Example: {'pattern': 'def main', 'path': '/home/user/src'}. NEVER call grep with empty {} or without 'pattern'."
            )
        if not path or not isinstance(path, str) or not path.strip():
            return ValidationResult(
                result=False,
                message="Missing required parameter 'path'. Example: {'pattern': 'def main', 'path': '/home/user/src'}. NEVER call grep without 'path'."
            )
        return ValidationResult(result=True)

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        import fnmatch

        pattern = args["pattern"]
        path = args["path"]
        glob_filter = args.get("glob")
        output_mode = args.get("output_mode", "content")

        if not os.path.isabs(path):
            root = getattr(context, "project_root", os.getcwd())
            path = os.path.join(root, path)

        results: List[Dict[str, Any]] = []
        file_matches: set = set()
        total_matches = 0

        try:
            compiled = re.compile(pattern)
        except re.error as e:
            return ToolResult(data={"error": f"Invalid regex: {e}"})

        files_to_search: List[str] = []
        if os.path.isfile(path):
            files_to_search = [path]
        elif os.path.isdir(path):
            for root_dir, _, files in os.walk(path):
                for fname in files:
                    if glob_filter and not fnmatch.fnmatch(fname, glob_filter):
                        continue
                    files_to_search.append(os.path.join(root_dir, fname))
        else:
            return ToolResult(data={"error": f"Path not found: {path}"})

        MAX_RESULTS = 500
        truncated = False
        for filepath in files_to_search:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, 1):
                        if compiled.search(line):
                            total_matches += 1
                            file_matches.add(filepath)
                            if output_mode == "content":
                                results.append({
                                    "file": os.path.relpath(filepath, path) if os.path.isdir(path) else filepath,
                                    "line": line_num,
                                    "text": line.rstrip("\n"),
                                })
                                if len(results) >= MAX_RESULTS:
                                    truncated = True
                                    break
            except Exception:
                continue
            if truncated:
                break

        if output_mode == "files_with_matches":
            return ToolResult(data={
                "matches": sorted(file_matches),
                "count": len(file_matches),
            })
        elif output_mode == "count_matches":
            return ToolResult(data={"count": total_matches})
        else:
            data: Dict[str, Any] = {
                "results": results,
                "count": total_matches,
            }
            if truncated:
                data["truncated"] = True
                data["note"] = f"Results limited to {MAX_RESULTS} matches. Use a more specific pattern or narrower path."
            return ToolResult(data=data)


class DiffTool(BaseTool):
    """Compare two files or texts and show differences.

    Useful for comparing netlist versions, schematic exports, or
    configuration files before/after changes.
    """

    name = "diff"
    aliases = ["compare", "cmp"]
    input_schema = {
        "type": "object",
        "properties": {
            "path_a": {
                "type": "string",
                "description": "Path to the first file (or 'text:' prefix for raw text).",
            },
            "path_b": {
                "type": "string",
                "description": "Path to the second file (or 'text:' prefix for raw text).",
            },
            "context_lines": {
                "type": "integer",
                "description": "Number of context lines around each change.",
                "default": 3,
            },
        },
        "required": ["path_a", "path_b"],
    }

    def description(self) -> str:
        return (
            "Compare two files or text strings and return a unified diff. "
            "Useful for netlist comparison, verifying file edits, or checking "
            "schematic/layout exports against golden references."
        )

    def validate_input(self, args: Dict[str, Any], context: Any) -> ValidationResult:
        path_a = args.get("path_a")
        path_b = args.get("path_b")
        if not path_a or not isinstance(path_a, str) or not path_a.strip():
            return ValidationResult(
                result=False,
                message="Missing required parameter 'path_a'. Example: {'path_a': '/home/user/file1.txt', 'path_b': '/home/user/file2.txt'}. NEVER call diff without 'path_a'."
            )
        if not path_b or not isinstance(path_b, str) or not path_b.strip():
            return ValidationResult(
                result=False,
                message="Missing required parameter 'path_b'. Example: {'path_a': '/home/user/file1.txt', 'path_b': '/home/user/file2.txt'}. NEVER call diff without 'path_b'."
            )
        return ValidationResult(result=True)

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        path_a = args.get("path_a", "")
        path_b = args.get("path_b", "")
        context_lines = args.get("context_lines", 3)

        def _read(src: str) -> tuple[List[str], str]:
            if src.startswith("text:"):
                text = src[5:]
                return text.splitlines(keepends=False), "<inline>"
            if not os.path.isfile(src):
                return [], src
            try:
                with open(src, "r", encoding="utf-8", errors="replace") as f:
                    return f.read().splitlines(keepends=False), src
            except Exception as e:
                return [], f"<error:{e}>"

        lines_a, label_a = _read(path_a)
        lines_b, label_b = _read(path_b)

        if not lines_a and label_a.startswith("<error"):
            return ToolResult(data={"error": f"Cannot read {path_a}: {label_a}"})
        if not lines_b and label_b.startswith("<error"):
            return ToolResult(data={"error": f"Cannot read {path_b}: {label_b}"})

        diff = list(unified_diff(
            lines_a, lines_b,
            fromfile=label_a, tofile=label_b,
            lineterm="",
            n=context_lines,
        ))

        return ToolResult(data={
            "has_differences": len(diff) > 0,
            "diff": "\n".join(diff) if diff else "Files are identical.",
            "lines_a": len(lines_a),
            "lines_b": len(lines_b),
        })
