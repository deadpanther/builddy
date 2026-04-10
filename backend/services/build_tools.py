"""Build chain membership, file maps, and diff helpers."""

from __future__ import annotations

import difflib
import json
from typing import Any

from sqlmodel import Session, select

from models import Build


def files_dict_from_build(build: Build) -> dict[str, str]:
    if build.generated_files:
        try:
            return json.loads(build.generated_files)
        except json.JSONDecodeError:
            return {}
    if build.generated_code:
        return {"index.html": build.generated_code}
    return {}


def collect_chain_ids(session: Session, build_id: str) -> set[str]:
    """All build IDs in the same version tree as *build_id*."""
    build = session.get(Build, build_id)
    if not build:
        return set()

    root_id = build_id
    visited: set[str] = {root_id}
    current = build
    while current.parent_build_id:
        if current.parent_build_id in visited:
            break
        root_id = current.parent_build_id
        visited.add(root_id)
        current = session.get(Build, root_id)
        if not current:
            break

    out: set[str] = set()
    queue = [root_id]
    seen_down: set[str] = set()
    while queue:
        cid = queue.pop(0)
        if cid in seen_down:
            continue
        seen_down.add(cid)
        out.add(cid)
        b = session.get(Build, cid)
        if not b:
            continue
        children = session.exec(select(Build).where(Build.parent_build_id == cid)).all()
        for child in children:
            queue.append(child.id)
    return out


def diff_builds(build_a: Build, build_b: Build) -> list[dict[str, Any]]:
    fa = files_dict_from_build(build_a)
    fb = files_dict_from_build(build_b)
    paths = sorted(set(fa) | set(fb))
    out: list[dict[str, Any]] = []
    for path in paths:
        ca = fa.get(path)
        cb = fb.get(path)
        if ca == cb:
            out.append({"path": path, "status": "unchanged", "unified_diff": ""})
        elif ca is None:
            diff_lines = list(
                difflib.unified_diff(
                    [],
                    cb.splitlines(),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            out.append({"path": path, "status": "added", "unified_diff": "\n".join(diff_lines)})
        elif cb is None:
            diff_lines = list(
                difflib.unified_diff(
                    ca.splitlines(),
                    [],
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            out.append({"path": path, "status": "removed", "unified_diff": "\n".join(diff_lines)})
        else:
            diff_lines = list(
                difflib.unified_diff(
                    ca.splitlines(),
                    cb.splitlines(),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            out.append({"path": path, "status": "changed", "unified_diff": "\n".join(diff_lines)})
    return out
