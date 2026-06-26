"""
Git Version Control Manager — programmatic Git operations for design files.

Provides a clean API for:
- Repository initialization and status
- Commit, diff, log operations
- Branch management
- File tracking (RTL, SDC, YAML configs, generated scripts)

Uses subprocess for Git operations. Compatible with Git 1.8+.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("implcraft.git")


@dataclass
class GitFileStatus:
    path: str
    status: str  # added, modified, deleted, untracked, renamed
    old_path: str = ""


@dataclass
class GitCommitInfo:
    commit_hash: str
    short_hash: str
    author: str
    email: str
    message: str
    date: datetime | None
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


@dataclass
class GitBranchInfo:
    name: str
    is_current: bool = False
    commit_hash: str = ""
    message: str = ""


@dataclass
class GitDiffResult:
    file_path: str
    diff_text: str
    additions: int = 0
    deletions: int = 0


@dataclass
class GitStatusResult:
    branch: str
    staged: list[GitFileStatus] = field(default_factory=list)
    unstaged: list[GitFileStatus] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    is_clean: bool = False


class GitManager:
    """
    Manages Git operations for design file version control.

    Usage:
        git = GitManager("/path/to/repo")
        status = git.status()
        git.add(["file1.v", "file2.sdc"])
        git.commit("Update RTL and constraints")
        log = git.log(count=10)
    """

    DESIGN_PATTERNS = [
        "*.v", "*.sv", "*.vh", "*.svh",
        "*.sdc", "*.upf", "*.cpf",
        "*.yaml", "*.yml", "*.json",
        "*.tcl", "*.py",
        "*.sp", "*.spi", "*.cdl",
        "*.lef", "*.def",
        "*.rpt", "*.log",
    ]

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path).resolve()
        self._validate_repo()

    def _validate_repo(self):
        """Ensure the path is a valid Git repository."""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a Git repository: {self.repo_path}")

    def _run_git(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a Git command in the repo directory."""
        cmd = ["git"] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.repo_path),
            )
            if check and result.returncode != 0:
                logger.error(f"Git command failed: {' '.join(cmd)}")
                logger.error(f"stderr: {result.stderr}")
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, result.stdout, result.stderr
                )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out: {' '.join(cmd)}")
            raise

    def status(self) -> GitStatusResult:
        """Get working tree status."""
        result = self._run_git(["status", "--porcelain", "--branch"])
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        branch = "unknown"
        staged = []
        unstaged = []
        untracked = []

        for line in lines:
            if not line:
                continue
            if line.startswith("##"):
                parts = line[3:].split("...")
                branch = parts[0].strip()
                continue

            index_status = line[0] if len(line) > 0 else " "
            work_status = line[1] if len(line) > 1 else " "
            file_path = line[3:].strip()

            if index_status == "?" and work_status == "?":
                untracked.append(file_path)
            else:
                if index_status != " ":
                    status_map = {
                        "A": "added", "M": "modified", "D": "deleted",
                        "R": "renamed", "C": "copied",
                    }
                    staged.append(GitFileStatus(
                        path=file_path,
                        status=status_map.get(index_status, "modified"),
                    ))
                if work_status != " ":
                    status_map = {
                        "M": "modified", "D": "deleted",
                    }
                    unstaged.append(GitFileStatus(
                        path=file_path,
                        status=status_map.get(work_status, "modified"),
                    ))

        return GitStatusResult(
            branch=branch,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            is_clean=(not staged and not unstaged and not untracked),
        )

    def add(self, files: list[str] | None = None, all_tracked: bool = False):
        """Stage files for commit."""
        if all_tracked:
            self._run_git(["add", "-u"])
        elif files:
            for f in files:
                self._run_git(["add", f])
        else:
            self._run_git(["add", "."])

    def commit(self, message: str, files: list[str] | None = None,
               author: str = "", email: str = "") -> GitCommitInfo | None:
        """Create a commit."""
        if files:
            self.add(files)

        status = self.status()
        if status.is_clean:
            logger.info("Nothing to commit, working tree clean")
            return None

        args = ["commit", "-m", message]
        if author:
            args.extend(["--author", f"{author} <{email}>"])

        self._run_git(args)
        return self.get_head_commit()

    def log(self, count: int = 20, branch: str = "") -> list[GitCommitInfo]:
        """Get commit log."""
        args = [
            "log", f"-{count}",
            "--format=%H|%h|%an|%ae|%s|%aI",
            "--shortstat",
        ]
        if branch:
            args.append(branch)

        result = self._run_git(args, check=False)
        if result.returncode != 0:
            return []

        commits = []
        lines = result.stdout.strip().split("\n")
        current_commit = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "|" in line and line.count("|") >= 5:
                if current_commit:
                    commits.append(current_commit)
                parts = line.split("|", 5)
                date = None
                try:
                    date = datetime.fromisoformat(parts[5])
                except (ValueError, IndexError):
                    try:
                        date = datetime.strptime(parts[5][:19], "%Y-%m-%dT%H:%M:%S")
                    except (ValueError, IndexError):
                        pass
                current_commit = GitCommitInfo(
                    commit_hash=parts[0],
                    short_hash=parts[1],
                    author=parts[2],
                    email=parts[3],
                    message=parts[4],
                    date=date,
                )
            elif "file" in line and ("insertion" in line or "deletion" in line):
                if current_commit:
                    nums = [int(s) for s in line.split() if s.isdigit()]
                    if len(nums) >= 1:
                        current_commit.files_changed = nums[0]
                    if len(nums) >= 2:
                        current_commit.insertions = nums[1]
                    if len(nums) >= 3:
                        current_commit.deletions = nums[2]

        if current_commit:
            commits.append(current_commit)

        return commits

    def diff(self, commit_a: str = "", commit_b: str = "HEAD",
             file_path: str = "") -> list[GitDiffResult]:
        """Get diff between commits or working tree."""
        args = ["diff", "--numstat"]

        if commit_a:
            args.append(commit_a)
            if commit_b:
                args.append(commit_b)

        if file_path:
            args.extend(["--", file_path])

        result = self._run_git(args, check=False)
        diffs = []

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    adds = int(parts[0]) if parts[0] != "-" else 0
                    dels = int(parts[1]) if parts[1] != "-" else 0
                    diffs.append(GitDiffResult(
                        file_path=parts[2],
                        diff_text="",
                        additions=adds,
                        deletions=dels,
                    ))
                except ValueError:
                    continue

        return diffs

    def diff_content(self, commit_a: str = "", commit_b: str = "HEAD",
                     file_path: str = "") -> str:
        """Get full diff content for a file."""
        args = ["diff"]
        if commit_a:
            args.append(commit_a)
            if commit_b:
                args.append(commit_b)
        else:
            args.append("HEAD")
        if file_path:
            args.extend(["--", file_path])

        result = self._run_git(args, check=False)
        return result.stdout

    def branches(self) -> list[GitBranchInfo]:
        """List all branches."""
        result = self._run_git(["branch", "-a"], check=False)
        branches = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            is_current = line.startswith("*")
            name = line.strip().lstrip("* ")
            branches.append(GitBranchInfo(
                name=name,
                is_current=is_current,
            ))
        return branches

    def current_branch(self) -> str:
        """Get current branch name."""
        result = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], check=False)
        if result.returncode != 0:
            return "unknown"
        return result.stdout.strip()

    def get_head_commit(self) -> GitCommitInfo | None:
        """Get the HEAD commit info."""
        commits = self.log(count=1)
        return commits[0] if commits else None

    def file_history(self, file_path: str, count: int = 20) -> list[GitCommitInfo]:
        """Get commit history for a specific file."""
        args = [
            "log", f"-{count}",
            "--format=%H|%h|%an|%ae|%s|%aI",
            "--", file_path,
        ]
        result = self._run_git(args, check=False)
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            parts = line.split("|", 5)
            if len(parts) < 6:
                continue
            date = None
            try:
                date = datetime.fromisoformat(parts[5])
            except (ValueError, IndexError):
                try:
                    date = datetime.strptime(parts[5][:19], "%Y-%m-%dT%H:%M:%S")
                except (ValueError, IndexError):
                    pass
            commits.append(GitCommitInfo(
                commit_hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                email=parts[3],
                message=parts[4],
                date=date,
            ))
        return commits

    def file_content_at(self, file_path: str, commit: str = "HEAD") -> str:
        """Get file content at a specific commit."""
        result = self._run_git(["show", f"{commit}:{file_path}"], check=False)
        if result.returncode != 0:
            return ""
        return result.stdout

    def pull(self, remote: str = "origin", branch: str = "") -> bool:
        """Pull from remote."""
        args = ["pull", remote]
        if branch:
            args.append(branch)
        result = self._run_git(args, check=False)
        return result.returncode == 0

    def push(self, remote: str = "origin", branch: str = "") -> bool:
        """Push to remote."""
        args = ["push", remote]
        if branch:
            args.append(branch)
        result = self._run_git(args, check=False)
        return result.returncode == 0
