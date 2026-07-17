"""
Git API — version control operations for design files.

Endpoints:
- GET    /api/git/status           — Get working tree status
- POST   /api/git/commit           — Commit changes
- GET    /api/git/log              — Get commit history
- GET    /api/git/diff             — Get diff between commits
- GET    /api/git/branches         — List branches
- GET    /api/git/file/{path}      — Get file content at HEAD
- GET    /api/git/file-history     — Get file commit history
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ..db.engine import get_session
from ..db.models import GitCommitRecord, DesignRecord
from ..db.schemas import GitCommitResponse, GitActionRequest, GitDiffRequest
from ..git.manager import GitManager

router = APIRouter()

# Default repo path from environment or project root
DEFAULT_REPO = os.environ.get("IMPLCRAFT_GIT_REPO", ".")


def _get_git_manager(repo_path: str = "") -> GitManager:
    """Get GitManager instance for the given repo."""
    path = repo_path or DEFAULT_REPO
    try:
        return GitManager(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _sync_commit_to_db(git: GitManager, design_id: int | None = None):
    """Sync latest Git commits to the database."""
    commits = git.log(count=20)
    with get_session() as session:
        for ci in commits:
            existing = session.query(GitCommitRecord).filter_by(
                commit_hash=ci.commit_hash
            ).first()
            if not existing:
                record = GitCommitRecord(
                    design_id=design_id,
                    commit_hash=ci.commit_hash,
                    short_hash=ci.short_hash,
                    author=ci.author,
                    email=ci.email,
                    message=ci.message,
                    branch=git.current_branch(),
                    files_changed=ci.files_changed,
                    insertions=ci.insertions,
                    deletions=ci.deletions,
                    committed_at=ci.date,
                )
                session.add(record)


@router.get("/git/status")
def git_status(repo_path: str = ""):
    """Get working tree status."""
    git = _get_git_manager(repo_path)
    status = git.status()
    return {
        "branch": status.branch,
        "is_clean": status.is_clean,
        "staged": [{"path": f.path, "status": f.status} for f in status.staged],
        "unstaged": [{"path": f.path, "status": f.status} for f in status.unstaged],
        "untracked": status.untracked,
    }


@router.post("/git/commit")
def git_commit(request: GitActionRequest):
    """Commit staged changes."""
    git = _get_git_manager(request.repo_path)

    if request.files:
        git.add(request.files)

    message = request.message or "Update design files"
    commit_info = git.commit(message)

    if commit_info:
        _sync_commit_to_db(git)
        return {
            "status": "committed",
            "commit_hash": commit_info.commit_hash,
            "short_hash": commit_info.short_hash,
            "message": commit_info.message,
            "author": commit_info.author,
        }
    return {"status": "no_changes", "message": "Nothing to commit"}


@router.get("/git/log", response_model=list[GitCommitResponse])
def git_log(
    repo_path: str = "",
    count: int = Query(default=20, le=100),
    sync: bool = False,
):
    """Get commit history."""
    git = _get_git_manager(repo_path)
    commits = git.log(count=count)

    if sync:
        _sync_commit_to_db(git)

    return [
        GitCommitResponse(
            id=0,
            design_id=None,
            commit_hash=c.commit_hash,
            short_hash=c.short_hash,
            author=c.author,
            email=c.email,
            message=c.message,
            branch=git.current_branch(),
            files_changed=c.files_changed,
            insertions=c.insertions,
            deletions=c.deletions,
            changed_files=[],
            committed_at=c.date.isoformat() if c.date else None,
            recorded_at=None,
        )
        for c in commits
    ]


@router.get("/git/diff")
def git_diff(
    repo_path: str = "",
    commit_a: str = "",
    commit_b: str = "HEAD",
    file_path: str = "",
):
    """Get diff between commits or working tree."""
    git = _get_git_manager(repo_path)

    if file_path:
        diff_text = git.diff_content(commit_a, commit_b, file_path)
        return {"diff": diff_text, "file_path": file_path}

    diffs = git.diff(commit_a, commit_b, file_path)
    return {
        "files": [
            {
                "path": d.file_path,
                "additions": d.additions,
                "deletions": d.deletions,
            }
            for d in diffs
        ]
    }


@router.get("/git/branches")
def git_branches(repo_path: str = ""):
    """List all branches."""
    git = _get_git_manager(repo_path)
    branches = git.branches()
    return {
        "current": git.current_branch(),
        "branches": [
            {
                "name": b.name,
                "is_current": b.is_current,
                "commit_hash": b.commit_hash,
                "message": b.message,
            }
            for b in branches
        ],
    }


@router.get("/git/file")
def git_file_content(
    file_path: str = Query(..., description="File path relative to repo root"),
    repo_path: str = "",
    commit: str = "HEAD",
):
    """Get file content at a specific commit."""
    git = _get_git_manager(repo_path)
    content = git.file_content_at(file_path, commit)
    if not content:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}@{commit}")
    return {
        "file_path": file_path,
        "commit": commit,
        "content": content,
        "size": len(content),
    }


@router.get("/git/file-history")
def git_file_history(
    file_path: str = Query(...),
    repo_path: str = "",
    count: int = Query(default=20, le=100),
):
    """Get commit history for a specific file."""
    git = _get_git_manager(repo_path)
    commits = git.file_history(file_path, count)
    return {
        "file_path": file_path,
        "commits": [
            {
                "commit_hash": c.commit_hash,
                "short_hash": c.short_hash,
                "author": c.author,
                "message": c.message,
                "date": c.date.isoformat() if c.date else None,
            }
            for c in commits
        ],
    }
