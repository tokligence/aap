import subprocess
from pathlib import Path
from typing import Optional

from .. import config


def _run_git(args: list[str], cwd: Optional[Path] = None) -> str:
    cmd = ["git"] + args
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git command failed: {' '.join(cmd)}")
    return (result.stdout or "").strip()


def ensure_repo(cwd: Optional[Path] = None) -> None:
    _run_git(["rev-parse", "--is-inside-work-tree"], cwd=cwd)


def has_staged_changes(cwd: Optional[Path] = None) -> bool:
    output = _run_git(["diff", "--cached", "--name-only"], cwd=cwd)
    return bool(output.strip())


def list_staged_files(cwd: Optional[Path] = None) -> list[str]:
    output = _run_git(["diff", "--cached", "--name-only"], cwd=cwd)
    return [line.strip() for line in output.splitlines() if line.strip()]


def stage_all(cwd: Optional[Path] = None) -> None:
    _run_git(["add", "-A"], cwd=cwd)


def create_commit(message: str, cwd: Optional[Path] = None, stage_all_changes: bool = False) -> str:
    ensure_repo(cwd)
    if stage_all_changes:
        stage_all(cwd=cwd)

    if not has_staged_changes(cwd=cwd):
        raise RuntimeError("No staged changes. Stage files or pass --stage-all.")

    _run_git(["commit", "-m", message], cwd=cwd)
    return _run_git(["rev-parse", "HEAD"], cwd=cwd)


def create_tag(tag_name: str, message: str, cwd: Optional[Path] = None) -> None:
    _run_git(["tag", "-a", tag_name, "-m", message], cwd=cwd)


def push(branch: Optional[str] = None, push_tags: bool = False, cwd: Optional[Path] = None) -> None:
    ensure_repo(cwd)
    push_args = ["push"]
    if branch:
        push_args.append("origin")
        push_args.append(branch)
    _run_git(push_args, cwd=cwd)
    if push_tags:
        _run_git(["push", "--tags"], cwd=cwd)


def default_repo_root() -> Path:
    return config.BASE_DIR.parent
