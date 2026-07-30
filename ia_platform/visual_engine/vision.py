"""Vision-assisted mockup understanding via Ollama multimodal models.

Describes a mockup image into a structured UI spec that the CodingAgent can follow.
If no vision model is installed / Ollama is offline, callers should degrade gracefully.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# Bump when the prompt/schema changes so disk cache invalidates.
VISION_PROMPT_VERSION = "v2-structured-json"

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

MOCKUP_VISION_PROMPT = f"""You are a senior UI/UX analyst converting a mockup image into an implementation spec.
Prompt-version: {VISION_PROMPT_VERSION}

Look at the image carefully. Reply with ONLY a single JSON object (no markdown fences, no prose outside JSON) using this schema:

{{
  "overview": "tipo de tela, densidade, estilo (dark/light/premium/minimal)",
  "style": "dark|light|mixed",
  "layout": ["estrutura de cima para baixo com proporções aproximadas"],
  "components": [{{"name": "…", "role": "…", "notes": "posição/estado/hierarquia"}}],
  "typography": {{"title": "tamanho/peso/cor relativo", "body": "…", "meta": "…"}},
  "colors": {{
    "background": "#RRGGBB",
    "surface": "#RRGGBB",
    "text": "#RRGGBB",
    "muted": "#RRGGBB",
    "border": "#RRGGBB",
    "accent": "#RRGGBB"
  }},
  "spacing": "paddings/gaps/raios/sombras observados",
  "visible_text": ["textos legíveis copiados do mockup"],
  "priorities": ["1. o mais importante para pixel-fidelity", "2. …", "3. …"]
}}

Rules:
- Use real hex colors when you can sample them; otherwise best-effort hex.
- Do not invent sections that are not visible.
- Prefer Portuguese (Brazil) for string values.
- Keep arrays short and concrete (max 8 items each).
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
        for name in names:
            if name == pref or name.lower() == pref.lower():
                return name

    lower_map = {n.lower(): n for n in names}
    for cand in PREFERRED_VISION_MODELS:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
        family = cand.split(":")[0].lower()
        family_hits = [n for n in names if n.lower().startswith(family)]
        if family_hits:
            return sorted(family_hits, key=lambda x: (len(x), x))[0]

    visionish = [n for n in names if is_vision_model_name(n)]
    if visionish:
        return sorted(visionish, key=lambda x: (len(x), x))[0]
    return None


def _ffmpeg_bin() -> Optional[str]:
    return shutil.which("ffmpeg")


def prepare_image_bytes(
    path: Path,
    *,
    max_edge: int = 1536,
    max_bytes: int = 3_800_000,
) -> Tuple[bytes, Dict[str, Any]]:
    """Load mockup bytes, optionally downscaling via ffmpeg for vision models."""
    path = Path(path)
    raw = path.read_bytes()
    meta: Dict[str, Any] = {"original_bytes": len(raw), "resized": False, "format": path.suffix.lower()}
    if len(raw) <= max_bytes and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        # Still downscale huge dimensions when ffmpeg is available (quality/latency).
        if len(raw) < 900_000 or not _ffmpeg_bin():
            return raw, meta

    ffmpeg = _ffmpeg_bin()
    if not ffmpeg:
        if len(raw) > max_bytes:
            raise ValueError(f"mockup too large for vision ({len(raw)} bytes) and ffmpeg unavailable")
        return raw, meta

    with tempfile.TemporaryDirectory(prefix="forge-vision-") as tmp:
        out = Path(tmp) / "vision.jpg"
        # scale so longest edge <= max_edge; force jpeg for smaller payloads
        vf = f"scale='min({max_edge},iw)':'min({max_edge},ih)':force_original_aspect_ratio=decrease"
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(path),
            "-vf",
            vf,
            "-q:v",
            "3",
            str(out),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            if len(raw) > max_bytes:
                raise ValueError(f"failed to resize mockup for vision: {exc}") from exc
            return raw, meta
        data = out.read_bytes()
        if not data:
            return raw, meta
        meta.update({"resized": True, "format": ".jpg", "vision_bytes": len(data)})
        return data, meta


def encode_image_base64(path: Path, *, max_bytes: int = 4_500_000) -> str:
    data, _meta = prepare_image_bytes(path, max_bytes=min(max_bytes, 3_800_000))
    if len(data) > max_bytes:
        raise ValueError(f"mockup too large for vision ({len(data)} bytes)")
    return base64.b64encode(data).decode("ascii")


def _cache_path(workspace: Path, mockup_path: Path, model: str) -> Path:
    raw = (
        f"{mockup_path.resolve()}::{model}::{mockup_path.stat().st_mtime_ns}"
        f"::{VISION_PROMPT_VERSION}"
    )
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
        "format": "json",
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
        # Some older vision models reject format=json — retry without it.
        if exc.code in {400, 422, 500} and "format" in (detail or "").lower():
            payload.pop("format", None)
            req = urllib.request.Request(
                f"{host}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        else:
            raise RuntimeError(f"vision chat HTTP {exc.code}: {detail or exc.reason}") from exc
    except Exception as exc:
        raise RuntimeError(f"vision chat failed: {exc}") from exc

    message = data.get("message") or {}
    content = (message.get("content") or data.get("response") or "").strip()
    if not content:
        raise RuntimeError("vision model returned empty content")
    content = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE).strip()
    return content


def parse_vision_payload(raw: str) -> Dict[str, Any]:
    """Parse model output into structured dict + markdown fallback spec."""
    text = (raw or "").strip()
    if not text:
        return {"structured": {}, "spec": ""}

    # Strip accidental fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    structured: Dict[str, Any] = {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            structured = parsed
    except json.JSONDecodeError:
        # Try first {...} blob
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    structured = parsed
            except json.JSONDecodeError:
                structured = {}

    if structured:
        spec = format_vision_spec_for_goal(structured, raw_fallback="")
        return {"structured": structured, "spec": spec or json.dumps(structured, ensure_ascii=False, indent=2)}
    return {"structured": {}, "spec": raw.strip()}


def format_vision_spec_for_goal(
    structured: Dict[str, Any],
    *,
    raw_fallback: str = "",
    max_chars: int = 4200,
) -> str:
    """Pack structured vision fields into a dense, priority-ordered goal block."""
    if not structured and raw_fallback:
        return raw_fallback.strip()[:max_chars]

    lines: List[str] = []
    overview = str(structured.get("overview") or "").strip()
    style = str(structured.get("style") or "").strip()
    if overview or style:
        lines.append("## Visão geral")
        if style:
            lines.append(f"- estilo: {style}")
        if overview:
            lines.append(f"- {overview}")

    colors = structured.get("colors") if isinstance(structured.get("colors"), dict) else {}
    if colors:
        lines.append("## Cores (hex)")
        for key in ("background", "surface", "text", "muted", "border", "accent"):
            val = str(colors.get(key) or "").strip()
            if val:
                lines.append(f"- {key}: {val}")

    layout = structured.get("layout") if isinstance(structured.get("layout"), list) else []
    if layout:
        lines.append("## Layout")
        for item in layout[:8]:
            text = str(item).strip()
            if text:
                lines.append(f"- {text}")

    components = structured.get("components") if isinstance(structured.get("components"), list) else []
    if components:
        lines.append("## Componentes")
        for item in components[:8]:
            if isinstance(item, dict):
                name = str(item.get("name") or "?").strip()
                role = str(item.get("role") or "").strip()
                notes = str(item.get("notes") or "").strip()
                chunk = f"- {name}"
                if role:
                    chunk += f" ({role})"
                if notes:
                    chunk += f": {notes}"
                lines.append(chunk)
            else:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")

    typography = structured.get("typography") if isinstance(structured.get("typography"), dict) else {}
    if typography:
        lines.append("## Tipografia")
        for key, val in typography.items():
            text = str(val).strip()
            if text:
                lines.append(f"- {key}: {text}")

    spacing = str(structured.get("spacing") or "").strip()
    if spacing:
        lines.append("## Espaçamento / forma")
        lines.append(f"- {spacing}")

    visible = structured.get("visible_text") if isinstance(structured.get("visible_text"), list) else []
    if visible:
        lines.append("## Textos visíveis")
        for item in visible[:10]:
            text = str(item).strip()
            if text:
                lines.append(f'- "{text}"')

    priorities = structured.get("priorities") if isinstance(structured.get("priorities"), list) else []
    if priorities:
        lines.append("## Prioridade de implementação")
        for idx, item in enumerate(priorities[:6], start=1):
            text = str(item).strip()
            if text:
                lines.append(f"{idx}. {text}")

    packed = "\n".join(lines).strip()
    if not packed:
        return (raw_fallback or "").strip()[:max_chars]
    if len(packed) <= max_chars:
        return packed
    # Prefer keeping colors + layout + priorities when truncating.
    head = "\n".join(lines[:18]).strip()
    return head[:max_chars]


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

    Returns dict with keys: ok, spec, structured, model, cached, path, error?
    """
    workspace = Path(workspace).resolve()
    raw = str(mockup_rel_or_abs or "").strip()
    if not raw:
        return {
            "ok": False,
            "error": "mockup path required",
            "spec": "",
            "structured": {},
            "model": None,
            "cached": False,
        }

    mockup_path = Path(raw)
    if not mockup_path.is_absolute():
        mockup_path = (workspace / mockup_path).resolve()
    try:
        mockup_path.relative_to(workspace)
    except ValueError:
        return {
            "ok": False,
            "error": "mockup outside workspace",
            "spec": "",
            "structured": {},
            "model": None,
            "cached": False,
        }
    if not mockup_path.is_file():
        return {
            "ok": False,
            "error": f"mockup not found: {raw}",
            "spec": "",
            "structured": {},
            "model": None,
            "cached": False,
        }

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
            "structured": {},
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
                    on_event(
                        {
                            "type": "vision.cached",
                            "model": chosen,
                            "path": str(mockup_path.relative_to(workspace)).replace("\\", "/"),
                            "preview": str(cached.get("spec") or "")[:1200],
                            "structured": bool(cached.get("structured")),
                        }
                    )
                return {
                    "ok": True,
                    "spec": str(cached["spec"]),
                    "structured": cached.get("structured") if isinstance(cached.get("structured"), dict) else {},
                    "model": chosen,
                    "cached": True,
                    "path": str(mockup_path.relative_to(workspace)).replace("\\", "/"),
                    "prompt_version": VISION_PROMPT_VERSION,
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
        raw_content = ollama_chat_with_image(
            host=host,
            model=chosen,
            prompt=MOCKUP_VISION_PROMPT,
            image_b64=image_b64,
            timeout=timeout,
            cancel_check=cancel_check,
        )
        parsed = parse_vision_payload(raw_content)
        spec = str(parsed.get("spec") or "").strip()
        structured = parsed.get("structured") if isinstance(parsed.get("structured"), dict) else {}
        if not spec:
            raise RuntimeError("vision model returned empty spec")
    except Exception as exc:  # noqa: BLE001
        if on_event:
            on_event({"type": "vision.failed", "model": chosen, "error": str(exc)})
        return {
            "ok": False,
            "error": str(exc),
            "spec": "",
            "structured": {},
            "model": chosen,
            "cached": False,
            "path": str(mockup_path.relative_to(workspace)).replace("\\", "/"),
        }

    rel = str(mockup_path.relative_to(workspace)).replace("\\", "/")
    payload = {
        "ok": True,
        "spec": spec,
        "structured": structured,
        "model": chosen,
        "cached": False,
        "path": rel,
        "duration_ms": int((time.time() - t0) * 1000),
        "prompt_version": VISION_PROMPT_VERSION,
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
                "preview": spec[:1200],
                "structured": bool(structured),
                "colors": (structured.get("colors") if isinstance(structured.get("colors"), dict) else {}),
            }
        )
    return payload
