"""Build compact live file-operation previews for the Forge UI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

MAX_PREVIEW_CHARS = 4500
MAX_LINES = 80


def _rel_path(workspace: Path, raw: Any) -> str:
    text = str(raw or "").strip().replace("\\", "/")
    if not text:
        return ""
    try:
        path = Path(text)
        if path.is_absolute():
            return str(path.resolve().relative_to(workspace.resolve())).replace("\\", "/")
    except Exception:
        pass
    return text.lstrip("./")


def _language_for(path: str) -> str:
    lower = path.lower()
    if lower.endswith((".html", ".htm")):
        return "html"
    if lower.endswith(".css"):
        return "css"
    if lower.endswith((".js", ".mjs", ".cjs")):
        return "javascript"
    if lower.endswith((".ts", ".tsx")):
        return "typescript"
    if lower.endswith(".jsx"):
        return "jsx"
    if lower.endswith(".py"):
        return "python"
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".md"):
        return "markdown"
    return "text"


def _clip_text(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n… (truncado)"


def _lines_from_text(text: str, *, kind: str = "context", start: int = 1) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for idx, line in enumerate(str(text or "").splitlines()[:MAX_LINES]):
        out.append({"n": start + idx, "text": line[:240], "kind": kind})
    return out


def _lines_from_diff(diff: str) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []
    n_old = 0
    n_new = 0
    hunk_re = re.compile(r"^@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@")
    for raw in str(diff or "").splitlines():
        if raw.startswith("---") or raw.startswith("+++"):
            continue
        match = hunk_re.match(raw)
        if match:
            n_old = int(match.group(1))
            n_new = int(match.group(2))
            lines.append({"n": n_new, "text": raw[:240], "kind": "hunk"})
            continue
        if raw.startswith("+"):
            lines.append({"n": n_new, "text": raw[1:241], "kind": "add"})
            n_new += 1
        elif raw.startswith("-"):
            lines.append({"n": n_old, "text": raw[1:241], "kind": "del"})
            n_old += 1
        elif raw.startswith("\\"):
            continue
        else:
            text = raw[1:] if raw.startswith(" ") else raw
            lines.append({"n": n_new or n_old, "text": text[:240], "kind": "context"})
            if n_new:
                n_new += 1
            if n_old:
                n_old += 1
        if len(lines) >= MAX_LINES:
            break
    return lines


def classify_op(tool: str) -> str:
    name = str(tool or "")
    if name in {"read_file", "read_file_range", "get_file_info"}:
        return "read"
    if name in {"write_file", "create_file", "create_multiple_files"}:
        return "write"
    if name in {"edit_file", "replace_in_file", "append_file", "append_to_file"}:
        return "edit"
    if name == "apply_patch":
        return "patch"
    if name == "delete_file":
        return "delete"
    if name in {"search_text", "search_files", "search_symbol", "search_relevant"}:
        return "search"
    if name in {"list_directory", "list_dir"}:
        return "list"
    if name.startswith("git_"):
        return "git"
    return "tool"


def _headline(op: str, path: str, status: str, tool: str) -> str:
    label = path or tool
    if status == "start":
        mapping = {
            "read": f"Lendo {label}",
            "write": f"Escrevendo {label}",
            "edit": f"Editando {label}",
            "patch": f"Aplicando patch em {label}",
            "delete": f"Apagando {label}",
            "search": f"Buscando em {label or 'projeto'}",
            "list": f"Listando {label or 'pasta'}",
            "git": f"Git: {tool}",
        }
        return mapping.get(op, f"Executando {tool}")
    if status == "error":
        return f"Falhou: {label}"
    mapping = {
        "read": f"Leu {label}",
        "write": f"Escreveu {label}",
        "edit": f"Editou {label}",
        "patch": f"Patch aplicado em {label}",
        "delete": f"Apagou {label}",
        "search": f"Busca concluída",
        "list": f"Listagem pronta",
    }
    return mapping.get(op, f"Concluiu {tool}")


def build_file_op_event(
    *,
    workspace: Path,
    tool: str,
    args: Optional[Dict[str, Any]],
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    args = args if isinstance(args, dict) else {}
    result = result if isinstance(result, dict) else {}
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    op = classify_op(tool)
    path = _rel_path(workspace, args.get("path") or data.get("path") or "")
    if not path and tool == "create_multiple_files":
        files = args.get("files") or data.get("files") or []
        if isinstance(files, list) and files:
            first = files[0] if not isinstance(files[0], dict) else files[0].get("path")
            path = _rel_path(workspace, first)

    lines: List[Dict[str, Any]] = []
    preview = ""
    diff = ""
    stats: Dict[str, Any] = {}

    if status == "start":
        if op == "write":
            content = str(args.get("content") or "")
            preview = _clip_text(content)
            lines = _lines_from_text(content, kind="add")
            stats = {"total_lines": len(content.splitlines()), "added": len(lines)}
        elif op == "edit":
            old = str(args.get("old") or "")
            new = str(args.get("new") or "")
            if old:
                lines.extend(_lines_from_text(old, kind="del"))
            if new:
                lines.extend(_lines_from_text(new, kind="add", start=max(1, int(args.get("line") or 1))))
            preview = _clip_text((("- " + old) if old else "") + (("\n+ " + new) if new else ""))
            stats = {"removed": 1 if old else 0, "added": 1 if new else 0}
        elif op == "patch":
            diff = str(args.get("diff") or "")
            if not diff and isinstance(args.get("hunks"), list):
                parts = []
                for hunk in args["hunks"][:12]:
                    if not isinstance(hunk, dict):
                        continue
                    if hunk.get("old"):
                        parts.append("-" + str(hunk.get("old")))
                    if hunk.get("new"):
                        parts.append("+" + str(hunk.get("new")))
                diff = "\n".join(parts)
            preview = _clip_text(diff)
            lines = _lines_from_diff(diff) if diff else []
        elif op == "read":
            start = int(args.get("start_line") or args.get("line") or 1)
            lines = [{"n": start, "text": "Abrindo arquivo…", "kind": "focus"}]
        elif op == "search":
            query = str(args.get("query") or args.get("pattern") or args.get("text") or "")
            lines = [{"n": 1, "text": f"query: {query[:200]}", "kind": "focus"}] if query else []
    else:
        if data.get("diff"):
            diff = str(data.get("diff"))
            preview = _clip_text(diff)
            lines = _lines_from_diff(diff)
            stats = {
                "added": sum(1 for line in lines if line.get("kind") == "add"),
                "removed": sum(1 for line in lines if line.get("kind") == "del"),
            }
        elif op == "write":
            content = str(args.get("content") or "")
            preview = _clip_text(content)
            lines = _lines_from_text(content, kind="add")
            stats = {"total_lines": data.get("total_lines") or len(content.splitlines()), "added": len(content.splitlines())}
        elif op == "edit":
            old = str(args.get("old") or "")
            new = str(args.get("new") or "")
            start = max(1, int(args.get("line") or data.get("line") or 1))
            if old:
                lines.extend(_lines_from_text(old, kind="del", start=start))
            if new:
                lines.extend(_lines_from_text(new, kind="add", start=start))
            preview = _clip_text((old and f"- {old}\n" or "") + (new and f"+ {new}" or ""))
            stats = {
                "lines_delta": data.get("lines_delta"),
                "total_lines": data.get("total_lines"),
                "added": 1 if new else 0,
                "removed": 1 if old else 0,
            }
        elif op == "read":
            content = str(data.get("content") or "")
            # content may be "12: line" numbered
            parsed: List[Dict[str, Any]] = []
            for raw in content.splitlines()[:MAX_LINES]:
                m = re.match(r"^(\d+):\s?(.*)$", raw)
                if m:
                    parsed.append({"n": int(m.group(1)), "text": m.group(2)[:240], "kind": "focus"})
                else:
                    parsed.append({"n": len(parsed) + 1, "text": raw[:240], "kind": "focus"})
            lines = parsed
            preview = _clip_text("\n".join(line["text"] for line in parsed))
            stats = {"total_lines": data.get("total_lines") or len(parsed)}

    ok = True if status == "start" else bool(result.get("ok", False))
    if status == "error" or error:
        ok = False
        status = "error"

    return {
        "type": "file_op",
        "op": op,
        "tool": tool,
        "path": path,
        "status": status,
        "ok": ok,
        "language": _language_for(path),
        "headline": _headline(op, path, status, tool),
        "preview": preview,
        "diff": _clip_text(diff, 3500) if diff else "",
        "lines": lines[:MAX_LINES],
        "stats": stats,
        "error": (error or result.get("error") or "")[:300] if not ok else "",
    }
