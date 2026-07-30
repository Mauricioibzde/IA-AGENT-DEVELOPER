"""Vision-assisted mockup understanding via Ollama multimodal models.

Describes a mockup image into a structured UI spec that the CodingAgent can follow.
If no vision model is installed / Ollama is offline, callers should degrade gracefully.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

VISION_NAME_HINTS = (
    "llava",
    "bakllava",
    "moondream",
    "minicpm-v",
    "minicpm_v",
    "qwen2-vl",
    "qwen2.5-vl",
    "qwen2vl",
    "llama3.2-vision",
    "gemma3",
    "vision",
)

PREFERRED_VISION_MODELS = (
    "llava:7b",
    "llava",
    "qwen2.5-vl:7b",
    "qwen2-vl:7b",
    "llama3.2-vision:11b",
    "llama3.2-vision",
    "moondream",
    "bakllava",
    "minicpm-v",
    "gemma3:4b",
)

MOCKUP_VISION_PROMPT = """You are a senior UI/UX analyst converting a mockup image into an implementation spec.

Describe the interface with precise, actionable detail for a coding agent.
Reply in Portuguese (Brazil), using this exact structure:

## Visão geral
- tipo de tela / propósito
- densidade (compacta/média/espaçada)
- estilo visual (dark/light, premium, minimal, etc.)

## Layout
- estrutura de cima para baixo (header, sidebar, main, footer, cards…)
- proporções aproximadas e alinhamentos
- breakpoints se parecer responsivo

## Componentes
- liste cada bloco importante (botões, inputs, tabelas, cards, tabs, badges…)
- hierarquia e estados visíveis (ativo/hover se aparente)

## Tipografia
- títulos/subtítulos/corpo: tamanho relativo, peso, cor

## Cores
- fundo, superfícies, bordas, texto, accent/primária, sucesso/erro se houver

## Espaçamento e forma
- paddings/gaps relativos, raios, sombras, bordas

## Conteúdo textual visível
- textos legíveis no mockup (copie quando possível)

## Prioridade de implementação
1. …
2. …
3. …

Seja concreto. Não invente seções que não aparecem na imagem.
"""


def is_vision_model_name(name: str) -> bool:
    lower = (name or "").strip().lower()
    if not lower:
        return False
    return any(hint in lower for hint in VISION_NAME_HINTS)


def pick_vision_model(
    installed: Sequence[str],
    *,
    preferred: Optional[str] = None,
) -> Optional[str]:
    """Pick the best available installed vision model."""
    names = [str(n).strip() for n in installed if str(n).strip()]
    if not names:
        return None

    if preferred:
        pref = preferred.strip()
        for name in names:
            if name == pref or name.startswith(pref + ":") or pref.startswith(name.split(":")[0]):
                if is_vision_model_name(name) or is_vision_model_name(pref):
                    return name
        # Explicit preferred even if not tagged vision (user override).
        for name in names:
            if name == pref or name.lower() == pref.lower():
                return name

    lower_map = {n.lower(): n for n in names}
    for cand in PREFERRED_VISION_MODELS:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
        # family match: llava:13b when asking llava
        family = cand.split(":")[0].lower()
        family_hits = [n for n in names if n.lower().startswith(family)]
        if family_hits:
            return sorted(family_hits, key=lambda x: (len(x), x))[0]

    visionish = [n for n in names if is_vision_model_name(n)]
    if visionish:
        return sorted(visionish, key=lambda x: (len(x), x))[0]
    return None


def encode_image_base64(path: Path, *, max_bytes: int = 4_500_000) -> str:
    data = Path(path).read_bytes()
    if len(data) > max_bytes:
        raise ValueError(f"mockup too large for vision ({len(data)} bytes)")
    return base64.b64encode(data).decode("ascii")


def _cache_path(workspace: Path, mockup_path: Path, model: str) -> Path:
    raw = f"{mockup_path.resolve()}::{model}::{mockup_path.stat().st_mtime_ns}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return Path(workspace).resolve() / ".agent" / "vision-cache" / f"{digest}.json"


def list_ollama_models(host: str, *, timeout: int = 8) -> List[str]:
    host = (host or "http://127.0.0.1:11434").rstrip("/")
    try:
        req = urllib.request.Request(f"{host}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def ollama_chat_with_image(
    *,
    host: str,
    model: str,
    prompt: str,
    image_b64: str,
    temperature: float = 0.1,
    timeout: int = 240,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> str:
    """Call Ollama /api/chat with a single image (multimodal)."""
    if cancel_check and cancel_check():
        raise RuntimeError("cancelled")
    host = host.rstrip("/")
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
    }
    req = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        raise RuntimeError(f"vision chat HTTP {exc.code}: {detail or exc.reason}") from exc
    except Exception as exc:
        raise RuntimeError(f"vision chat failed: {exc}") from exc

    message = data.get("message") or {}
    content = (message.get("content") or data.get("response") or "").strip()
    if not content:
        raise RuntimeError("vision model returned empty content")
    # Strip common think wrappers if present.
    content = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE).strip()
    return content


def describe_mockup(
    workspace: Path,
    mockup_rel_or_abs: str,
    *,
    host: str = "http://127.0.0.1:11434",
    model: Optional[str] = None,
    use_cache: bool = True,
    timeout: int = 240,
    cancel_check: Optional[Callable[[], bool]] = None,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Describe a mockup image into a structured UI specification.

    Returns dict with keys: ok, spec, model, cached, path, error?
    """
    workspace = Path(workspace).resolve()
    raw = str(mockup_rel_or_abs or "").strip()
    if not raw:
        return {"ok": False, "error": "mockup path required", "spec": "", "model": None, "cached": False}

    mockup_path = Path(raw)
    if not mockup_path.is_absolute():
        mockup_path = (workspace / mockup_path).resolve()
    try:
        mockup_path.relative_to(workspace)
    except ValueError:
        return {"ok": False, "error": "mockup outside workspace", "spec": "", "model": None, "cached": False}
    if not mockup_path.is_file():
        return {"ok": False, "error": f"mockup not found: {raw}", "spec": "", "model": None, "cached": False}

    installed = list_ollama_models(host)
    chosen = pick_vision_model(installed, preferred=model)
    if not chosen:
        return {
            "ok": False,
            "error": (
                "Nenhum modelo de visão instalado no Ollama "
                "(ex.: llava, qwen2.5-vl, llama3.2-vision, moondream)."
            ),
            "spec": "",
            "model": None,
            "cached": False,
            "installed": installed,
        }

    cache_file = _cache_path(workspace, mockup_path, chosen)
    if use_cache and cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("spec"):
                if on_event:
                    on_event({"type": "vision.cached", "model": chosen, "path": str(mockup_path.relative_to(workspace))})
                return {
                    "ok": True,
                    "spec": str(cached["spec"]),
                    "model": chosen,
                    "cached": True,
                    "path": str(mockup_path.relative_to(workspace)).replace("\\", "/"),
                }
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    if on_event:
        on_event(
            {
                "type": "vision.started",
                "model": chosen,
                "path": str(mockup_path.relative_to(workspace)).replace("\\", "/"),
            }
        )

    t0 = time.time()
    try:
        image_b64 = encode_image_base64(mockup_path)
        spec = ollama_chat_with_image(
            host=host,
            model=chosen,
            prompt=MOCKUP_VISION_PROMPT,
            image_b64=image_b64,
            timeout=timeout,
            cancel_check=cancel_check,
        )
    except Exception as exc:  # noqa: BLE001
        if on_event:
            on_event({"type": "vision.failed", "model": chosen, "error": str(exc)})
        return {
            "ok": False,
            "error": str(exc),
            "spec": "",
            "model": chosen,
            "cached": False,
            "path": str(mockup_path.relative_to(workspace)).replace("\\", "/"),
        }

    rel = str(mockup_path.relative_to(workspace)).replace("\\", "/")
    payload = {
        "ok": True,
        "spec": spec,
        "model": chosen,
        "cached": False,
        "path": rel,
        "duration_ms": int((time.time() - t0) * 1000),
    }
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    if on_event:
        on_event(
            {
                "type": "vision.completed",
                "model": chosen,
                "path": rel,
                "chars": len(spec),
                "duration_ms": payload["duration_ms"],
            }
        )
    return payload
